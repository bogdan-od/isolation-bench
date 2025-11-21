#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define CHUNK_SIZE (10 * 1024 * 1024) // 10 MB

int main() {
    long long total_allocated = 0;
    while(1) {
        void* mem = malloc(CHUNK_SIZE);
        if (mem == NULL) {
            fprintf(stderr, "malloc failed! Total allocated: %lld MB\n", total_allocated / (1024*1024));
            perror("malloc");
            sleep(1);
            
            return 1;
        }
        
        memset(mem, 0xAA, CHUNK_SIZE);
        total_allocated += CHUNK_SIZE;
        fprintf(stdout, "Total allocated: %lld MB\n", total_allocated / (1024*1024));
        fflush(stdout);
        
        usleep(50000); // 50ms
    }
    return 0;
}
