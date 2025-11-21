#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>

int main() {
    printf("Attempting to create raw socket...\n");
    
    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    
    if (sock < 0) {
        printf("Raw socket BLOCKED: %s\n", strerror(errno));
        return 1;
    }
    
    printf("Raw socket CREATED successfully (CAP_NET_RAW granted)\n");
    close(sock);
    return 0;
}
