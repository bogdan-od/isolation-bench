#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>

void* burn_cpu(void* arg) {
    long duration = (long)arg;
    time_t start = time(NULL);
    volatile unsigned long counter = 0;
    
    while (time(NULL) - start < duration) {
        counter++;
        // Some actual work to prevent optimization
        if (counter % 1000000 == 0) {
            counter ^= counter >> 1;
        }
    }
    return NULL;
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <duration_seconds>\n", argv[0]);
        return 1;
    }
    
    int duration = atoi(argv[1]);
    int num_threads = sysconf(_SC_NPROCESSORS_ONLN);
    if (num_threads <= 0) num_threads = 4;
    
    printf("Burning CPU with %d threads for %d seconds...\n", num_threads, duration);
    
    pthread_t* threads = malloc(num_threads * sizeof(pthread_t));
    
    for (int i = 0; i < num_threads; i++) {
        pthread_create(&threads[i], NULL, burn_cpu, (void*)(long)duration);
    }
    
    for (int i = 0; i < num_threads; i++) {
        pthread_join(threads[i], NULL);
    }
    
    free(threads);
    printf("CPU burn completed\n");
    return 0;
}
