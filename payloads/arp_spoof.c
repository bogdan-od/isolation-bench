#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <netinet/if_ether.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <errno.h>

int main() {
    printf("Attempting ARP spoofing...\n");
    
    // Try to create raw socket for ARP
    int sock = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ARP));
    
    if (sock < 0) {
        printf("ARP socket BLOCKED: %s\n", strerror(errno));
        return 1;
    }
    
    printf("ARP socket created - potential for spoofing!\n");
    close(sock);
    return 0;
}
