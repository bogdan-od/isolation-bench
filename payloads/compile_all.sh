#!/bin/bash
# Compile all test payload binaries

set -e

echo "==================================="
echo "Compiling IsolationBench Payloads"
echo "==================================="

# Check if gcc is available
if ! command -v gcc &> /dev/null; then
    echo "ERROR: gcc not found. Please install build-essential or equivalent."
    exit 1
fi

# List of all C source files (without .c extension)
PAYLOADS=(
    "fork_bomb"
    "memory_hog"
    "cpu_burn"
    "disk_bomb"
    "dev_probe"
    "port_scanner"
    "raw_socket_test"
    "reboot_attempt"
    "ptrace_test"
    "chroot_escape"
    "cgroup_escape"
    "arp_spoof"
    "process_thrash"
    "fd_bomb"
    "signal_storm"
    "mount_attacker"
    "syscall_tester"
)

SUCCESS=0
FAILED=0

for payload in "${PAYLOADS[@]}"; do
    if [ -f "${payload}.c" ]; then
        echo -n "Compiling ${payload}.c ... "
        if gcc -static -o "${payload}" "${payload}.c" -pthread 2>/dev/null; then
            echo "SUCCESS"
            ((SUCCESS++))
        else
            echo "FAILED"
            ((FAILED++))
        fi
    else
        echo "WARNING: ${payload}.c not found, skipping"
    fi
done

echo ""
echo "==================================="
echo "Compilation Summary"
echo "==================================="
echo "Successful: $SUCCESS"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ All payloads compiled successfully!"
    exit 0
else
    echo "⚠ Some payloads failed to compile"
    exit 1
fi
