#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <target_mb>\n", argv[0]);
        return 1;
    }
    
    int target_mb = atoi(argv[1]);
    const int chunk_size = 1024 * 1024; // 1MB
    char* buffer = malloc(chunk_size);
    if (!buffer) {
        perror("malloc");
        return 1;
    }
    
    memset(buffer, 'A', chunk_size);
    
    int fd = open("/tmp/disk_bomb.dat", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        perror("open");
        free(buffer);
        return 1;
    }
    
    printf("Attempting to write %d MB to disk...\n", target_mb);
    
    int written_mb = 0;
    for (int i = 0; i < target_mb; i++) {
        ssize_t result = write(fd, buffer, chunk_size);
        if (result < 0) {
            perror("write error");
            break;
        }
        written_mb++;
        if (written_mb % 50 == 0) {
            printf("Written: %d MB\n", written_mb);
        }
    }
    
    close(fd);
    free(buffer);
    unlink("/tmp/disk_bomb.dat");
    
    printf("Total written: %d MB\n", written_mb);
    return written_mb >= target_mb ? 0 : 1;
}
