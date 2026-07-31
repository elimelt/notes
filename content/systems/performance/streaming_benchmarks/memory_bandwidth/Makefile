CC = gcc
CFLAGS = -O3 -Wall -Wextra -std=c99 -march=native -mtune=native
LDFLAGS = -lpthread

TARGET = benchmark
SOURCE = benchmark.c

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE) $(LDFLAGS)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

.PHONY: all clean run
