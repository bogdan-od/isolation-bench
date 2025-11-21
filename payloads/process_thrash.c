#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <errno.h>
#include <string.h>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <num_processes>\n", argv[0]);
        return 1;
    }
    
    int num_procs = atoi(argv[1]);
    printf("Creating and destroying %d processes...\n", num_procs);
    
    for (int i = 0; i < num_procs; i++) {
        pid_t pid = fork();
        
        if (pid < 0) {
            printf("Fork failed at iteration %d: %s\n", i, strerror(errno));
            return 1;
        }
        
        if (pid == 0) {
            // Child: exit immediately
            exit(0);
        } else {
            // Parent: wait for child
            waitpid(pid, NULL, 0);
        }
        
        if ((i + 1) % 100 == 0) {
            printf("Progress: %d/%d\n", i + 1, num_procs);
        }
    }
    
    printf("Process thrashing completed successfully\n");
    return 0;
}
