# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

FROM ubuntu:26.04

ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LANGUAGE=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs wget curl ca-certificates tar unzip xz-utils \
    build-essential bc bison flex python3 clang-22 llvm-22 lld \
    libelf-dev libssl-dev libdwarf-dev libdw-dev cpio \
    dwarves rsync python3 device-tree-compiler \
    lz4 zstd libncurses-dev bash jq \
    binutils-aarch64-linux-gnu file ccache \
    openssl libssl-dev dkms libelf-dev libudev-dev libpciaccess-dev libiberty-dev \
    zlib1g-dev \
    libx11-dev libgl1-mesa-dev \
    libxml2-16 libxml2-utils xsltproc \
  && if [ "$TARGETARCH" = "amd64" ]; then \
       apt-get install -y --no-install-recommends libc6-dev-i386 lib32z1-dev; \
     fi \
  && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends libclang-22-dev \
  && rm -rf /var/lib/apt/lists/*

RUN ln -sf /bin/bash /bin/sh
RUN ln -sf /usr/bin/python3 /usr/bin/python

ENV LIBCLANG_PATH=/usr/lib/llvm-22/lib \
    HOSTCFLAGS=-I/usr/include/libdwarf
