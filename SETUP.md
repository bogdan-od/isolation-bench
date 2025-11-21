# IsolationBench Setup Guide

This guide provides detailed setup instructions for IsolationBench on various Linux distributions.

## Table of Contents

- [Ubuntu/Debian Setup](#ubuntudebian-setup)
- [RHEL/CentOS/Fedora Setup](#rhelcentosfedora-setup)
- [Arch Linux Setup](#arch-linux-setup)
- [Docker Setup](#docker-setup)
- [gVisor Setup](#gvisor-setup)
- [Kata Containers Setup](#kata-containers-setup)
- [QEMU Setup](#qemu-setup)
- [NsJail Setup](#nsjail-setup)
- [Troubleshooting](#troubleshooting)

---

## Ubuntu/Debian Setup

### 1. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install basic build tools
sudo apt install -y \
    build-essential \
    git \
    python3 \
    python3-pip \
    python3-venv

# Install Docker
sudo apt install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# Install QEMU (optional)
sudo apt install -y qemu-system-x86 qemu-utils

# Install development libraries
sudo apt install -y \
    automake \
    libtool \
    pkg-config
```

### 2. Install Python Dependencies

```bash
cd IsolationBench
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Build Test Environment

```bash
# Download sysbench
wget https://github.com/akopytov/sysbench/archive/refs/tags/1.0.20.tar.gz

# Build Docker image
docker build -t isolation_env:latest .
```

### 4. Compile Payloads

```bash
cd payloads
chmod +x compile_all.sh
./compile_all.sh
cd ..
```

---

## RHEL/CentOS/Fedora Setup

### 1. Install System Dependencies

```bash
# RHEL/CentOS
sudo yum groupinstall -y "Development Tools"
sudo yum install -y python3 python3-pip git

# Fedora
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y python3 python3-pip git

# Install Docker
sudo yum install -y docker
# or for Fedora
sudo dnf install -y docker

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

### 2. Follow Ubuntu steps 2-4 above

---

## Arch Linux Setup

```bash
# Install dependencies
sudo pacman -S base-devel python python-pip docker qemu-full

# Enable Docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

# Follow Ubuntu steps 2-4
```

---

## Docker Setup

Docker is the primary test environment for IsolationBench.

### Verify Installation

```bash
docker --version
docker run hello-world
```

### Common Issues

**Permission denied when running Docker**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in, or:
newgrp docker
```

**Docker service not running**
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

---

## gVisor Setup

gVisor provides a sandboxed container runtime.

### Installation (Ubuntu/Debian)

```bash
# Add gVisor repository
curl -fsSL https://gvisor.dev/archive.key | sudo apt-key add -
sudo add-apt-repository "deb https://storage.googleapis.com/gvisor/releases release main"

# Install runsc
sudo apt update
sudo apt install -y runsc

# Configure Docker to use runsc
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "runtimes": {
    "runsc": {
      "path": "/usr/bin/runsc"
    }
  }
}
EOF

sudo systemctl restart docker
```

### Verify Installation

```bash
docker run --rm --runtime=runsc hello-world
```

### Update config.yaml

```yaml
tools:
  docker:
    runtime_gvisor: "runsc"
```

---

## Kata Containers Setup

Kata Containers provides VM-based container isolation.

### Installation (Ubuntu 20.04+)

```bash
# Install from Kata packages
sudo sh -c "echo 'deb http://download.opensuse.org/repositories/home:/katacontainers:/releases:/x86_64:/stable-2.0/xUbuntu_$(lsb_release -rs)/ /' > /etc/apt/sources.list.d/kata-containers.list"

curl -sL  http://download.opensuse.org/repositories/home:/katacontainers:/releases:/x86_64:/stable-2.0/xUbuntu_$(lsb_release -rs)/Release.key | sudo apt-key add -

sudo apt update
sudo apt install -y kata-runtime kata-containers-image

# Configure containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml

# Add Kata runtime to Docker
sudo tee -a /etc/docker/daemon.json <<EOF
{
  "runtimes": {
    "kata": {
      "path": "/usr/bin/kata-runtime"
    }
  }
}
EOF

sudo systemctl restart docker
```

### Verify Installation

```bash
docker run --rm --runtime=kata hello-world
```

### Update config.yaml

```yaml
tools:
  docker:
    runtime_kata: "kata-runtime"
```

---

## QEMU Setup

QEMU is used for full VM-based tests.

### Installation

```bash
# Ubuntu/Debian
sudo apt install -y qemu-system-x86 qemu-utils

# Fedora
sudo dnf install -y qemu-system-x86 qemu-img

# Arch
sudo pacman -S qemu-full
```

### Create Test VM Image

You need a QEMU VM image with SSH access. Here's a quick setup:

```bash
# Download a cloud image (Ubuntu example)
wget https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img

# Resize image
qemu-img resize focal-server-cloudimg-amd64.img 10G

# Create cloud-init configuration for SSH
cat > user-data <<EOF
#cloud-config
password: testpassword
chpasswd: { expire: False }
ssh_pwauth: True
EOF

# Create a cloud-init ISO
cloud-localds user-data.img user-data

# Boot VM once to initialize
qemu-system-x86_64 \
    -m 2048 \
    -smp 2 \
    -enable-kvm \
    -hda focal-server-cloudimg-amd64.img \
    -drive file=user-data.img,format=raw \
    -net nic -net user,hostfwd=tcp::2222-:22 \
    -nographic
```

### Update config.yaml

```yaml
tools:
  qemu:
    image_path: "/path/to/focal-server-cloudimg-amd64.img"
    ssh_port: 2222
    ssh_user: "ubuntu"
    ssh_pass: "testpassword"
```

---

## NsJail Setup

NsJail provides lightweight sandboxing using Linux namespaces.

### Installation

```bash
# Install dependencies
sudo apt install -y \
    autoconf \
    bison \
    flex \
    gcc \
    g++ \
    git \
    libprotobuf-dev \
    libnl-route-3-dev \
    libtool \
    make \
    pkg-config \
    protobuf-compiler

# Clone and build
git clone https://github.com/google/nsjail.git
cd nsjail
make
sudo cp nsjail /usr/local/bin/
cd ..
```

### Create Rootfs

```bash
# Export Docker container as rootfs
docker export $(docker create isolation_env:latest) | tar -C /tmp/nsjail-root -xf -

# Or create minimal rootfs
mkdir -p /tmp/nsjail-root
# Copy necessary files
```

### Update config.yaml

```yaml
tools:
  nsjail:
    path: "/usr/local/bin/nsjail"
    rootfs: "/tmp/nsjail-root"
```

---

## Troubleshooting

### "Permission denied" when running tests

```bash
# Ensure you're running with sudo
sudo python3 main.py
```

### Docker runtime not found

```bash
# Verify runtime configuration
docker info | grep -i runtime

# Check daemon.json
cat /etc/docker/daemon.json
```

### QEMU VM won't boot

```bash
# Check KVM support
lsmod | grep kvm

# Enable KVM (if available)
sudo modprobe kvm
sudo modprobe kvm_intel  # or kvm_amd
```

### Payload compilation errors

```bash
# Ensure gcc is installed
gcc --version

# Install missing dependencies
sudo apt install -y build-essential

# Try compiling individually
cd payloads
gcc -static -o fork_bomb fork_bomb.c
```

### Python module not found

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Tests timing out

Edit `config.yaml`:
```yaml
global_settings:
  default_timeout: 60  # Increase timeout
```

---

## Verification

After setup, verify everything works:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run a simple test
sudo python3 main.py

# Check results
ls -lh results/
cat results/summary.md
```

---

## Next Steps

- Review [README.md](README.md) for usage instructions
- Customize `config.yaml` for your tests
- Read [CONTRIBUTING.md](CONTRIBUTING.md) to add new tests

---

## Getting Help

- Check [GitHub Issues](https://github.com/bogdan-od/IsolationBench/issues)
- Review error logs in `results/`
- Ensure all prerequisites are installed
