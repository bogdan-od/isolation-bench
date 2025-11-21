#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>

int scan_port(const char* host, int port) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return -1;
    }
    
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    
    if (inet_pton(AF_INET, host, &addr.sin_addr) <= 0) {
        close(sock);
        return -1;
    }
    
    struct timeval timeout;
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    
    int result = connect(sock, (struct sockaddr*)&addr, sizeof(addr));
    close(sock);
    
    return result;
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <host> <port1> [port2] ...\n", argv[0]);
        return 1;
    }
    
    const char* host = argv[1];
    printf("Scanning %s...\n", host);
    
    int open_count = 0;
    for (int i = 2; i < argc; i++) {
        int port = atoi(argv[i]);
        int result = scan_port(host, port);
        
        if (result == 0) {
            printf("Port %d: OPEN\n", port);
            open_count++;
        } else {
            printf("Port %d: closed/filtered (%s)\n", port, strerror(errno));
        }
    }
    
    printf("Total open ports: %d\n", open_count);
    return 0;
}
