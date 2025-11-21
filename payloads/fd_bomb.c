#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <target_fd_count>\n", argv[0]);
        return 1;
    }
    
    int target = atoi(argv[1]);
    printf("Attempting to open %d file descriptors...\n", target);
    
    int* fds = malloc(target * sizeof(int));
    if (!fds) {
        perror("malloc");
        return 1;
    }
    
    int opened = 0;
    for (int i = 0; i < target; i++) {
        fds[i] = open("/dev/null", O_RDONLY);
        if (fds[i] < 0) {
            printf("FD limit hit at %d: %s\n", i, strerror(errno));
            break;
        }
        opened++;
        
        if ((i + 1) % 500 == 0) {
            printf("Opened: %d FDs\n", i + 1);
        }
    }
    
    // Cleanup
    for (int i = 0; i < opened; i++) {
        close(fds[i]);
    }
    free(fds);
    
    printf("Total FDs opened: %d\n", opened);
    return opened >= target ? 0 : 1;
}
