FROM debian:bookworm-slim
RUN apt update && apt install -y --no-install-recommends \
    build-essential automake libtool pkg-config wget \
    bash tcpdump netcat-openbsd iproute2 procps util-linux \
    && rm -rf /var/lib/apt/lists/*

COPY 1.0.20.tar.gz /tmp/
RUN tar xzf /tmp/1.0.20.tar.gz && cd sysbench-1.0.20 \
    && ./autogen.sh \
    && ./configure --disable-luajit --without-mysql --without-pgsql \
    && make -j$(nproc) \
    && make install \
    && cd .. && rm -rf sysbench-1.0.20 /tmp/1.0.20.tar.gz


COPY payloads/* /bin/
RUN chmod +x /bin/*
