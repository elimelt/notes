CC = clang
CFLAGS = -O3 -Wall -std=c11 -march=armv8.5-a+simd

all: benchmark

benchmark: benchmark.c
	$(CC) $(CFLAGS) -o benchmark benchmark.c

clean:
	rm -f benchmark
