#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>

const char* dangerous_devices[] = {
    "/dev/mem",
    "/dev/kmem",
    "/dev/port",
    NULL
};

int main() {
    printf("Probing sensitive devices:\n");
    int accessible_count = 0;
    
    for (int i = 0; dangerous_devices[i] != NULL; i++) {
        const char* dev = dangerous_devices[i];
        int fd = open(dev, O_RDONLY);
        
        if (fd >= 0) {
            printf("%s: accessible\n", dev);
            accessible_count++;
            close(fd);
        } else {
            printf("%s: blocked (%s)\n", dev, strerror(errno));
        }
    }
    
    printf("Total accessible: %d\n", accessible_count);
    return accessible_count > 0 ? 0 : 1;
}
