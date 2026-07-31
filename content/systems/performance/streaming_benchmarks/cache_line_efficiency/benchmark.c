#define _POSIX_C_SOURCE 200112L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <string.h>

#define CACHE_LINE 64
#define GB (1024UL * 1024UL * 1024UL)
#define SIZE (1UL * GB)
#define RUNS 5

static inline double now_sec(void)
{
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec + ts.tv_nsec * 1e-9;
}

double seq_partial(uint8_t *buf, size_t n)
{
  volatile uint64_t s = 0;
  double t0 = now_sec();
  for (size_t i = 0; i < n; i += CACHE_LINE)
    s += *(uint64_t *)(buf + i);
  double t1 = now_sec();
  if (s == 42)
    puts("");
  return (n / CACHE_LINE * 8) / (t1 - t0) / 1e9;
}

double seq_full(uint8_t *buf, size_t n)
{
  volatile uint64_t s = 0;
  double t0 = now_sec();
  for (size_t i = 0; i < n; i += CACHE_LINE)
  {
    __attribute__((aligned(16))) uint8_t tmp[CACHE_LINE];
    memcpy(tmp, buf + i, CACHE_LINE);
    s += tmp[0];
  }
  double t1 = now_sec();
  if (s == 42)
    puts("");
  return (n) / (t1 - t0) / 1e9;
}

double rand_chase(uint8_t *buf, size_t n)
{
  size_t lines = n / CACHE_LINE;
  size_t *idx = (size_t *)malloc(lines * sizeof(size_t));
  for (size_t i = 0; i < lines; i++)
    idx[i] = i;
  for (size_t i = lines - 1; i > 0; i--)
  {
    size_t j = rand() % (i + 1);
    size_t t = idx[i];
    idx[i] = idx[j];
    idx[j] = t;
  }
  size_t *next = (size_t *)malloc(lines * sizeof(size_t));
  for (size_t i = 0; i < lines - 1; i++)
    next[idx[i]] = idx[i + 1];
  next[idx[lines - 1]] = idx[0];
  size_t p = 0;
  volatile uint64_t s = 0;
  double t0 = now_sec();
  for (size_t i = 0; i < lines; i++)
  {
    uint64_t *x = (uint64_t *)(buf + p * CACHE_LINE);
    s += *x;
    p = next[p];
  }
  double t1 = now_sec();
  free(idx);
  free(next);
  if (s == 42)
    puts("");
  return (lines * 8) / (t1 - t0) / 1e9;
}

int main()
{
  void *buf;
  posix_memalign(&buf, CACHE_LINE, SIZE);
  memset(buf, 1, SIZE);
  double p = 0, f = 0, r = 0;
  for (int i = 0; i < RUNS; i++)
  {
    p += seq_partial((uint8_t *)buf, SIZE);
    f += seq_full((uint8_t *)buf, SIZE);
    r += rand_chase((uint8_t *)buf, SIZE);
  }
  p /= RUNS;
  f /= RUNS;
  r /= RUNS;
  printf("seq8,seq64,rand8\n");
  printf("%.2f,%.2f,%.2f\n", p, f, r);
  free(buf);
}
