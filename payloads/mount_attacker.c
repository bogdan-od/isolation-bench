#include <stdio.h>
#include <sys/mount.h>
#include <errno.h>

int main() {
    const char* source = "/dev/sda1";
    const char* target = "/mnt/attack";
    const char* fstype = "ext4";
    
    printf("Attempting to mount %s at %s...\n", source, target);

    if (mount(source, target, fstype, MS_RDONLY, NULL) == -1) {
        perror("mount");
        fprintf(stderr, "Mount attack FAILED (as expected).\n");
        return 1;
    }

    fprintf(stdout, "Mount attack SUCCESSFUL! (This is BAD!)\n");
    umount(target);
    return 0;
}
