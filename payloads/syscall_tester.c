#include <stdio.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <errno.h>
#include <linux/reboot.h>
#include <string.h>

#ifndef __NR_add_key
#define __NR_add_key 248
#endif

#ifndef __NR_reboot
#define __NR_reboot 169
#endif

int main() {
    int failed_calls = 0;
    long ret;

    printf("Attempting potentially blocked syscalls...\n");

    errno = 0;
    ret = syscall(__NR_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2, LINUX_REBOOT_CMD_RESTART, 0);
    if (ret == -1) {
        printf("syscall(reboot): BLOCKED (errno: %d, %s)\n", errno, strerror(errno));
    } else {
        printf("syscall(reboot): SUCCESS (This is BAD!)\n");
        failed_calls++;
    }

    errno = 0;
    ret = syscall(__NR_add_key, "user", "testkey", "testdata", 8, 0);
    if (ret == -1) {
        printf("syscall(add_key): BLOCKED (errno: %d, %s)\n", errno, strerror(errno));
    } else {
        printf("syscall(add_key): SUCCESS (Return code: %ld)\n", ret);
    }

    return failed_calls;
}
