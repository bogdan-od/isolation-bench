#include <stdio.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <target_pid>\n", argv[0]);
        return 1;
    }
    
    pid_t target = atoi(argv[1]);
    printf("Attempting to ptrace PID %d...\n", target);
    
    long result = ptrace(PTRACE_ATTACH, target, NULL, NULL);
    
    if (result < 0) {
        printf("Ptrace BLOCKED: %s\n", strerror(errno));
        return 1;
    }
    
    printf("CRITICAL: Ptrace succeeded on PID %d!\n", target);
    ptrace(PTRACE_DETACH, target, NULL, NULL);
    return 0;
}
