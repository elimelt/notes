#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>
#include <time.h>

#if !defined(__x86_64__)
#error "store_fwd_bench requires x86-64"
#endif

#ifndef STORE_FWD_BUILD_FLAGS
#define STORE_FWD_BUILD_FLAGS "unrecorded"
#endif

enum {
  PATTERN_COUNT = 3,
  MAX_SAMPLES = 101,
  WARMUP_ITERATIONS = 1000000,
};

#if defined(__clang__)
#define STORE_FWD_COMPILER "clang " __clang_version__
#elif defined(__GNUC__)
#define STORE_FWD_COMPILER "gcc " __VERSION__
#else
#define STORE_FWD_COMPILER "unknown " __VERSION__
#endif

typedef uint64_t (*runner_fn)(uint64_t iterations, uint64_t salt);

static _Alignas(64) unsigned char bytes[128];
static volatile uint64_t checksum_sink;

static inline uint64_t exact_step(unsigned char *base, uint64_t value) {
  uint64_t loaded;
  __asm__ volatile(
      "movq %[value], 0(%[base])\n\t"
      "movq 0(%[base]), %[loaded]"
      : [loaded] "=&r"(loaded)
      : [base] "r"(base), [value] "r"(value)
      : "memory");
  return loaded;
}

static inline uint64_t overlap_step(unsigned char *base, uint64_t value) {
  uint64_t loaded;
  __asm__ volatile(
      "movq %[value], 1(%[base])\n\t"
      "movq 0(%[base]), %[loaded]"
      : [loaded] "=&r"(loaded)
      : [base] "r"(base), [value] "r"(value)
      : "memory");
  return loaded;
}

static inline uint64_t independent_step(unsigned char *base, uint64_t value) {
  uint64_t loaded;
  __asm__ volatile(
      "movq %[value], 0(%[base])\n\t"
      "movq 64(%[base]), %[loaded]"
      : [loaded] "=&r"(loaded)
      : [base] "r"(base), [value] "r"(value)
      : "memory");
  return loaded;
}

#define DEFINE_RUNNER(name)                                                   \
  static __attribute__((noinline)) uint64_t run_##name(                       \
      uint64_t iterations, uint64_t salt) {                                   \
    uint64_t checksum = salt;                                                 \
    for (uint64_t i = 0; i < iterations; ++i) {                               \
      checksum += name##_step(bytes, i + salt);                               \
    }                                                                         \
    return checksum;                                                          \
  }

DEFINE_RUNNER(exact)
DEFINE_RUNNER(overlap)
DEFINE_RUNNER(independent)

static const char *const pattern_names[PATTERN_COUNT] = {
    "exact", "partial_overlap", "independent"};

static const runner_fn runners[PATTERN_COUNT] = {
    run_exact, run_overlap, run_independent};

static void prepare_bytes(void) {
  memset(bytes, 0xa5, sizeof(bytes));
}

static uint64_t monotonic_raw_ns(void) {
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0) {
    perror("clock_gettime");
    exit(1);
  }
  return (uint64_t)ts.tv_sec * UINT64_C(1000000000) + (uint64_t)ts.tv_nsec;
}

static double measure(int pattern, uint64_t iterations, uint64_t salt,
                      uint64_t *checksum) {
  prepare_bytes();
  const uint64_t start = monotonic_raw_ns();
  *checksum = runners[pattern](iterations, salt);
  const uint64_t elapsed = monotonic_raw_ns() - start;
  return (double)elapsed / (double)iterations;
}

static uint64_t xorshift64(uint64_t *state) {
  uint64_t value = *state;
  value ^= value << 13;
  value ^= value >> 7;
  value ^= value << 17;
  *state = value;
  return value;
}

static void prepare_balanced_orders(int samples,
                                    int orders[MAX_SAMPLES][PATTERN_COUNT]) {
  uint64_t random_state = UINT64_C(0x6a09e667f3bcc909);
  for (int block = 0; block < samples / PATTERN_COUNT; ++block) {
    int base[PATTERN_COUNT] = {0, 1, 2};
    for (int i = PATTERN_COUNT - 1; i > 0; --i) {
      const int j = (int)(xorshift64(&random_state) % (uint64_t)(i + 1));
      const int temporary = base[i];
      base[i] = base[j];
      base[j] = temporary;
    }
    const int direction = (xorshift64(&random_state) & 1) != 0 ? 1 : -1;
    for (int row = 0; row < PATTERN_COUNT; ++row) {
      for (int position = 0; position < PATTERN_COUNT; ++position) {
        const int index =
            (row + direction * position + PATTERN_COUNT) % PATTERN_COUNT;
        orders[block * PATTERN_COUNT + row][position] = base[index];
      }
    }
  }
}

static int compare_double(const void *left, const void *right) {
  const double a = *(const double *)left;
  const double b = *(const double *)right;
  return (a > b) - (a < b);
}

static uint64_t parse_u64(const char *text, const char *name) {
  char *end = NULL;
  if (text[0] == '-' || text[0] == '+') {
    fprintf(stderr, "invalid %s: %s\n", name, text);
    exit(2);
  }
  errno = 0;
  const unsigned long long value = strtoull(text, &end, 10);
  if (errno != 0 || end == text || *end != '\0') {
    fprintf(stderr, "invalid %s: %s\n", name, text);
    exit(2);
  }
  return (uint64_t)value;
}

static int affinity_cpu(void) {
  cpu_set_t set;
  CPU_ZERO(&set);
  if (sched_getaffinity(0, sizeof(set), &set) != 0) {
    perror("sched_getaffinity");
    exit(1);
  }

  int only_cpu = -1;
  for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) {
    if (!CPU_ISSET(cpu, &set)) {
      continue;
    }
    if (only_cpu != -1) {
      fprintf(stderr, "run under taskset with exactly one allowed CPU\n");
      exit(2);
    }
    only_cpu = cpu;
  }
  if (only_cpu == -1) {
    fprintf(stderr, "empty CPU affinity mask\n");
    exit(2);
  }
  return only_cpu;
}

static void print_cpu_model(void) {
  FILE *cpuinfo = fopen("/proc/cpuinfo", "r");
  if (cpuinfo == NULL) {
    printf("cpu_model=unavailable\n");
    return;
  }

  char line[512];
  while (fgets(line, sizeof(line), cpuinfo) != NULL) {
    const char *prefix = "model name";
    if (strncmp(line, prefix, strlen(prefix)) != 0) {
      continue;
    }
    char *value = strchr(line, ':');
    if (value == NULL) {
      continue;
    }
    ++value;
    while (*value == ' ' || *value == '\t') {
      ++value;
    }
    value[strcspn(value, "\r\n")] = '\0';
    printf("cpu_model=%s\n", value);
    fclose(cpuinfo);
    return;
  }

  fclose(cpuinfo);
  printf("cpu_model=unavailable\n");
}

static void print_environment(uint64_t iterations, int samples, int cpu) {
  struct utsname system;
  if (uname(&system) != 0) {
    perror("uname");
    exit(1);
  }

  printf("architecture=x86_64\n");
  print_cpu_model();
  printf("kernel=%s %s %s\n", system.sysname, system.release,
         system.machine);
  printf("compiler=%s\n", STORE_FWD_COMPILER);
  printf("build_flags=%s\n", STORE_FWD_BUILD_FLAGS);
  printf("affinity_cpu=%d\n", cpu);
  printf("timer=CLOCK_MONOTONIC_RAW\n");
  printf("measurement=elapsed wall time for the complete loop; no baseline subtraction\n");
  printf("accesses=8-byte movq store then 8-byte movq load at offsets exact 0/0, partial_overlap 1/0, independent 0/64\n");
  printf("iterations_per_sample=%" PRIu64 "\n", iterations);
  printf("warmup_iterations_per_pattern=%d\n", WARMUP_ITERATIONS);
  printf("samples_per_pattern=%d\n", samples);
  printf("order_seed=0x6a09e667f3bcc909\n");
}

int main(int argc, char **argv) {
  const uint64_t iterations =
      argc > 1 ? parse_u64(argv[1], "iterations") : UINT64_C(20000000);
  const uint64_t parsed_samples =
      argc > 2 ? parse_u64(argv[2], "samples") : UINT64_C(21);
  if (argc > 3 || iterations < 1000 || parsed_samples < 9 ||
      parsed_samples > MAX_SAMPLES || parsed_samples % 2 == 0 ||
      parsed_samples % PATTERN_COUNT != 0) {
    fprintf(stderr,
            "usage: %s [iterations>=1000] "
            "[odd samples from 9 to %d, divisible by 3]\n",
            argv[0], MAX_SAMPLES);
    return 2;
  }
  const int samples = (int)parsed_samples;
  const int cpu = affinity_cpu();

  double timings[PATTERN_COUNT][MAX_SAMPLES] = {{0.0}};
  int orders[MAX_SAMPLES][PATTERN_COUNT] = {{0}};
  uint64_t checksums[PATTERN_COUNT] = {0};
  prepare_balanced_orders(samples, orders);

  for (int pattern = 0; pattern < PATTERN_COUNT; ++pattern) {
    prepare_bytes();
    checksum_sink ^= runners[pattern](WARMUP_ITERATIONS,
                                      UINT64_C(0x10000) + (uint64_t)pattern);
  }

  for (int sample = 0; sample < samples; ++sample) {
    for (int position = 0; position < PATTERN_COUNT; ++position) {
      const int pattern = orders[sample][position];
      const uint64_t salt = (uint64_t)(sample + 1) * UINT64_C(0x100000001b3) +
                            (uint64_t)pattern;
      uint64_t checksum = 0;
      timings[pattern][sample] =
          measure(pattern, iterations, salt, &checksum);
      checksums[pattern] ^= checksum;
    }
  }

  print_environment(iterations, samples, cpu);
  for (int sample = 0; sample < samples; ++sample) {
    printf("trial_order[%d]=%s,%s,%s\n", sample + 1,
           pattern_names[orders[sample][0]], pattern_names[orders[sample][1]],
           pattern_names[orders[sample][2]]);
  }

  printf("\nraw_samples_ns_per_op\n");
  printf("sample,exact,partial_overlap,independent\n");
  for (int sample = 0; sample < samples; ++sample) {
    printf("%d,%.6f,%.6f,%.6f\n", sample + 1, timings[0][sample],
           timings[1][sample], timings[2][sample]);
  }

  printf("\nsummary_ns_per_op\n");
  printf("pattern,min,p25,median,p75,max,checksum_xor\n");
  for (int pattern = 0; pattern < PATTERN_COUNT; ++pattern) {
    double sorted[MAX_SAMPLES];
    memcpy(sorted, timings[pattern], (size_t)samples * sizeof(sorted[0]));
    qsort(sorted, (size_t)samples, sizeof(sorted[0]), compare_double);
    printf("%s,%.6f,%.6f,%.6f,%.6f,%.6f,0x%016" PRIx64 "\n",
           pattern_names[pattern], sorted[0], sorted[samples / 4],
           sorted[samples / 2], sorted[(3 * samples) / 4],
           sorted[samples - 1], checksums[pattern]);
  }

  checksum_sink ^= checksums[0] ^ checksums[1] ^ checksums[2];
  return checksum_sink == UINT64_MAX ? 1 : 0;
}
