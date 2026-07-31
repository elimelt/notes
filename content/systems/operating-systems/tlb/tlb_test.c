#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/mman.h>

#define PAGE_SIZE 16384
#define MAX_PAGES 8192  // 128MB working set
#define ROUNDS 500

typedef struct node {
    struct node *next;
    char pad[PAGE_SIZE - sizeof(struct node *)];
} node_t;

static inline uint64_t timer(void) {
    uint64_t val;
    __asm__ __volatile__("mrs %0, cntvct_el0" : "=r"(val));
    return val;
}

static inline void barrier(void) {
    __asm__ __volatile__("dmb sy" ::: "memory");
}

int main(void) {
    uint64_t freq;
    __asm__ __volatile__("mrs %0, cntfrq_el0" : "=r"(freq));
    
    printf("pages,ns_per_chase\n");
    
    for (int num_pages = 1; num_pages <= MAX_PAGES; num_pages++) {
        size_t size = (size_t)num_pages * PAGE_SIZE;
        node_t *mem = mmap(NULL, size, PROT_READ | PROT_WRITE,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        
        if (mem == MAP_FAILED) {
            fprintf(stderr, "mmap failed at %d pages\n", num_pages);
            break;
        }
        
        // Shuffle pages for random access pattern
        int *order = malloc(num_pages * sizeof(int));
        for (int i = 0; i < num_pages; i++) order[i] = i;
        
        for (int i = num_pages - 1; i > 0; i--) {
            int j = rand() % (i + 1);
            int tmp = order[i]; 
            order[i] = order[j]; 
            order[j] = tmp;
        }
        
        // Build circular linked list in random order
        for (int i = 0; i < num_pages - 1; i++) {
            node_t *curr = (node_t *)((char *)mem + order[i] * PAGE_SIZE);
            node_t *next = (node_t *)((char *)mem + order[i + 1] * PAGE_SIZE);
            curr->next = next;
        }
        node_t *last = (node_t *)((char *)mem + order[num_pages - 1] * PAGE_SIZE);
        last->next = (node_t *)((char *)mem + order[0] * PAGE_SIZE);
        
        free(order);
        
        // Warmup
        node_t *p = mem;
        for (int i = 0; i < num_pages * 3; i++) 
            p = p->next;
        
        // Measure
        barrier();
        uint64_t start = timer();
        barrier();
        
        for (int round = 0; round < ROUNDS; round++) {
            for (int i = 0; i < num_pages; i++) {
                p = p->next;
            }
        }
        
        barrier();
        uint64_t end = timer();
        barrier();
        
        if (p == NULL) printf("impossible\n");
        
        double ns = ((double)(end - start) / (ROUNDS * num_pages)) * (1e9 / freq);
        printf("%d,%.3f\n", num_pages, ns);
        fflush(stdout);
        
        munmap(mem, size);
    }
    
    return 0;
}
