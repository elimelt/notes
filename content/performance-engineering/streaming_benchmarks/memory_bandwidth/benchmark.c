#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>
#include <stdint.h>

#ifndef MAP_HUGETLB
#define MAP_HUGETLB 0
#endif

#define BUFFER_SIZE_GB 1
#define BUFFER_SIZE (BUFFER_SIZE_GB * 1024ULL * 1024ULL * 1024ULL)
#define ITERATIONS 3
#define WARMUP_ITERATIONS 1
#define RANDOM_ACCESS_COUNT (1024 * 1024)
typedef enum {
    SEQUENTIAL_READ,
    SEQUENTIAL_WRITE,
    SEQUENTIAL_COPY,
    RANDOM_READ,
    RANDOM_WRITE,
    RANDOM_COPY
} access_pattern_t;

typedef struct {
    double bandwidth_gbps;
    double time_seconds;
    size_t bytes_processed;
    access_pattern_t pattern;
} benchmark_result_t;

static inline uint64_t get_time_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

static void* allocate_aligned_buffer(size_t size) {
    void* ptr = mmap(NULL, size, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0);
    if (ptr == MAP_FAILED) {
        ptr = aligned_alloc(4096, size);
    }
    return ptr;
}

static void deallocate_buffer(void* ptr, size_t size) {
    if (munmap(ptr, size) != 0) {
        free(ptr);
    }
}

static benchmark_result_t benchmark_sequential_read(char* buffer, size_t size) {
    benchmark_result_t result = {0};
    result.pattern = SEQUENTIAL_READ;
    result.bytes_processed = size;
    result.time_seconds = 0.0;

    volatile char sum = 0;
    uint64_t start = get_time_ns();

    for (size_t i = 0; i < size; i++) {
        sum += buffer[i];
    }

    uint64_t end = get_time_ns();
    result.time_seconds = (end - start) / 1e9;
    result.bandwidth_gbps = (size / result.time_seconds) / 1e9;

    if (sum == 0) printf("Sum: %d\n", sum);

    return result;
}

static benchmark_result_t benchmark_sequential_write(char* buffer, size_t size) {
    benchmark_result_t result = {0};
    result.pattern = SEQUENTIAL_WRITE;
    result.bytes_processed = size;
    result.time_seconds = 0.0;

    uint64_t start = get_time_ns();

    for (size_t i = 0; i < size; i++) {
        buffer[i] = (char)(i & 0xFF);
    }

    uint64_t end = get_time_ns();
    result.time_seconds = (end - start) / 1e9;
    result.bandwidth_gbps = (size / result.time_seconds) / 1e9;

    return result;
}

static benchmark_result_t benchmark_sequential_copy(char* src, char* dst, size_t size) {
    benchmark_result_t result = {0};
    result.pattern = SEQUENTIAL_COPY;
    result.bytes_processed = size * 2;
    result.time_seconds = 0.0;

    uint64_t start = get_time_ns();

    memcpy(dst, src, size);

    uint64_t end = get_time_ns();
    result.time_seconds = (end - start) / 1e9;
    result.bandwidth_gbps = (result.bytes_processed / result.time_seconds) / 1e9;

    return result;
}

static benchmark_result_t benchmark_random_read(char* buffer, size_t size) {
    benchmark_result_t result = {0};
    result.pattern = RANDOM_READ;
    result.bytes_processed = RANDOM_ACCESS_COUNT;
    result.time_seconds = 0.0;

    volatile char sum = 0;
    uint64_t start = get_time_ns();

    srand(42);
    for (size_t i = 0; i < RANDOM_ACCESS_COUNT; i++) {
        size_t idx = rand() % size;
        sum += buffer[idx];
    }

    uint64_t end = get_time_ns();
    result.time_seconds = (end - start) / 1e9;
    result.bandwidth_gbps = (result.bytes_processed / result.time_seconds) / 1e9;

    if (sum == 0) printf("Sum: %d\n", sum);

    return result;
}

static benchmark_result_t benchmark_random_write(char* buffer, size_t size) {
    benchmark_result_t result = {0};
    result.pattern = RANDOM_WRITE;
    result.bytes_processed = RANDOM_ACCESS_COUNT;
    result.time_seconds = 0.0;

    uint64_t start = get_time_ns();

    srand(42);
    for (size_t i = 0; i < RANDOM_ACCESS_COUNT; i++) {
        size_t idx = rand() % size;
        buffer[idx] = (char)(i & 0xFF);
    }

    uint64_t end = get_time_ns();
    result.time_seconds = (end - start) / 1e9;
    result.bandwidth_gbps = (result.bytes_processed / result.time_seconds) / 1e9;

    return result;
}

static benchmark_result_t benchmark_random_copy(char* src, char* dst, size_t size) {
    benchmark_result_t result = {0};
    result.pattern = RANDOM_COPY;
    result.bytes_processed = RANDOM_ACCESS_COUNT * 2;
    result.time_seconds = 0.0;

    uint64_t start = get_time_ns();

    srand(42);
    for (size_t i = 0; i < RANDOM_ACCESS_COUNT; i++) {
        size_t src_idx = rand() % size;
        size_t dst_idx = rand() % size;
        dst[dst_idx] = src[src_idx];
    }

    uint64_t end = get_time_ns();
    result.time_seconds = (end - start) / 1e9;
    result.bandwidth_gbps = (result.bytes_processed / result.time_seconds) / 1e9;

    return result;
}

static const char* pattern_name(access_pattern_t pattern) {
    switch (pattern) {
        case SEQUENTIAL_READ: return "Sequential Read";
        case SEQUENTIAL_WRITE: return "Sequential Write";
        case SEQUENTIAL_COPY: return "Sequential Copy";
        case RANDOM_READ: return "Random Read";
        case RANDOM_WRITE: return "Random Write";
        case RANDOM_COPY: return "Random Copy";
        default: return "Unknown";
    }
}

static void run_benchmark_suite() {
    printf("Memory Bandwidth Benchmark\n");
    printf("==========================\n");
    printf("Buffer size: %d GB\n", BUFFER_SIZE_GB);
    printf("Iterations: %d (after %d warmup)\n\n", ITERATIONS, WARMUP_ITERATIONS);

    char* buffer1 = (char*)allocate_aligned_buffer(BUFFER_SIZE);
    char* buffer2 = (char*)allocate_aligned_buffer(BUFFER_SIZE);

    if (!buffer1 || !buffer2) {
        fprintf(stderr, "Failed to allocate memory\n");
        exit(1);
    }

    printf("Initializing buffer...\n");
    for (size_t i = 0; i < BUFFER_SIZE; i++) {
        buffer1[i] = (char)(i & 0xFF);
    }

    benchmark_result_t results[6];

    for (int pattern = 0; pattern < 6; pattern++) {
        printf("Running %s benchmark...\n", pattern_name((access_pattern_t)pattern));

        double total_bandwidth = 0.0;

        for (int i = 0; i < WARMUP_ITERATIONS; i++) {
            switch (pattern) {
                case SEQUENTIAL_READ:
                    benchmark_sequential_read(buffer1, BUFFER_SIZE);
                    break;
                case SEQUENTIAL_WRITE:
                    benchmark_sequential_write(buffer1, BUFFER_SIZE);
                    break;
                case SEQUENTIAL_COPY:
                    benchmark_sequential_copy(buffer1, buffer2, BUFFER_SIZE);
                    break;
                case RANDOM_READ:
                    benchmark_random_read(buffer1, BUFFER_SIZE);
                    break;
                case RANDOM_WRITE:
                    benchmark_random_write(buffer1, BUFFER_SIZE);
                    break;
                case RANDOM_COPY:
                    benchmark_random_copy(buffer1, buffer2, BUFFER_SIZE);
                    break;
            }
        }

        for (int i = 0; i < ITERATIONS; i++) {
            benchmark_result_t result;
            switch (pattern) {
                case SEQUENTIAL_READ:
                    result = benchmark_sequential_read(buffer1, BUFFER_SIZE);
                    break;
                case SEQUENTIAL_WRITE:
                    result = benchmark_sequential_write(buffer1, BUFFER_SIZE);
                    break;
                case SEQUENTIAL_COPY:
                    result = benchmark_sequential_copy(buffer1, buffer2, BUFFER_SIZE);
                    break;
                case RANDOM_READ:
                    result = benchmark_random_read(buffer1, BUFFER_SIZE);
                    break;
                case RANDOM_WRITE:
                    result = benchmark_random_write(buffer1, BUFFER_SIZE);
                    break;
                case RANDOM_COPY:
                    result = benchmark_random_copy(buffer1, buffer2, BUFFER_SIZE);
                    break;
                default:
                    continue;
            }
            total_bandwidth += result.bandwidth_gbps;
        }

        results[pattern].bandwidth_gbps = total_bandwidth / ITERATIONS;
        results[pattern].pattern = (access_pattern_t)pattern;
        results[pattern].bytes_processed = BUFFER_SIZE;
        if (pattern == SEQUENTIAL_COPY || pattern == RANDOM_COPY) {
            results[pattern].bytes_processed *= 2;
        }
    }

    printf("\nResults:\n");
    printf("========\n");
    printf("%-20s %12s\n", "Pattern", "Bandwidth (GB/s)");
    printf("%-20s %12s\n", "-------", "----------------");

    // Note: Theoretical bandwidth varies by system configuration
    // and cannot be accurately determined without system-specific information

    for (int i = 0; i < 6; i++) {
        printf("%-20s %12.2f\n",
               pattern_name(results[i].pattern),
               results[i].bandwidth_gbps);
    }

    printf("\nAnalysis:\n");
    printf("=========\n");

    double best_sequential = 0.0;
    for (int i = 0; i < 3; i++) {
        if (results[i].bandwidth_gbps > best_sequential) {
            best_sequential = results[i].bandwidth_gbps;
        }
    }

    printf("Best sequential performance: %.2f GB/s\n", best_sequential);

    double best_random = 0.0;
    for (int i = 3; i < 6; i++) {
        if (results[i].bandwidth_gbps > best_random) {
            best_random = results[i].bandwidth_gbps;
        }
    }

    double random_efficiency = (best_random / best_sequential) * 100.0;
    printf("Random access efficiency: %.1f%% of sequential (%.2f GB/s vs %.2f GB/s)\n",
           random_efficiency, best_random, best_sequential);

    deallocate_buffer(buffer1, BUFFER_SIZE);
    deallocate_buffer(buffer2, BUFFER_SIZE);
}

int main() {
    printf("System Information:\n");
    printf("==================\n");

    long pages = sysconf(_SC_PHYS_PAGES);
    long page_size = sysconf(_SC_PAGE_SIZE);
    long total_memory = pages * page_size;

    printf("Total memory: %.2f GB\n", total_memory / (1024.0 * 1024.0 * 1024.0));
    printf("Page size: %ld bytes\n", page_size);
    printf("CPU cores: %ld\n", sysconf(_SC_NPROCESSORS_ONLN));

    printf("\n");

    run_benchmark_suite();

    return 0;
}
