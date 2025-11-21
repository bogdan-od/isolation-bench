#include <stdio.h>
#include <signal.h>
#include <unistd.h>
#include <time.h>
#include <stdlib.h>

volatile int signal_count = 0;

void signal_handler(int sig) {
    signal_count++;
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <duration_seconds>\n", argv[0]);
        return 1;
    }
    
    int duration = atoi(argv[1]);
    
    signal(SIGUSR1, signal_handler);
    
    pid_t child = fork();
    if (child < 0) {
        perror("fork");
        return 1;
    }
    
    if (child == 0) {
        // Child: send signals rapidly
        time_t start = time(NULL);
        while (time(NULL) - start < duration) {
            kill(getppid(), SIGUSR1);
        }
        exit(0);
    } else {
        // Parent: receive signals
        sleep(duration + 1);
        printf("Received %d signals in %d seconds\n", signal_count, duration);
        return 0;
    }
}
