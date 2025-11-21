#include <stdio.h>
#include <unistd.h>
#include <sys/reboot.h>
#include <errno.h>
#include <string.h>

int main() {
    printf("Attempting reboot syscall...\n");
    
    // Try to reboot (will fail if properly isolated)
    int result = reboot(RB_AUTOBOOT);
    
    if (result < 0) {
        printf("Reboot BLOCKED: %s\n", strerror(errno));
        return 1;
    }
    
    printf("CRITICAL: Reboot syscall succeeded!\n");
    return 0;
}
