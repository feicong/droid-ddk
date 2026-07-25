# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

FROM ubuntu:26.04

ARG TARGETARCH
ARG LIBXML2_COMPAT_URL=https://download.gnome.org/sources/libxml2/2.9/libxml2-2.9.14.tar.xz
ARG LIBXML2_COMPAT_SHA256=60d74a257d1ccec0475e749cba2f21559e48139efba6ff28224357c7c798dfee

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

RUN set -eux; \
    curl --retry 3 --retry-all-errors -fsSL "$LIBXML2_COMPAT_URL" -o /tmp/libxml2.tar.xz; \
    echo "$LIBXML2_COMPAT_SHA256  /tmp/libxml2.tar.xz" | sha256sum -c -; \
    tar -xJf /tmp/libxml2.tar.xz -C /tmp; \
    cd /tmp/libxml2-2.9.14; \
    PATH=/usr/bin:/bin CC=gcc CXX=g++ ./configure \
      --prefix=/opt/droid-ddk/compat \
      --without-python --without-lzma --without-iconv --without-readline \
      --disable-static; \
    PATH=/usr/bin:/bin make -j"$(nproc)"; \
    PATH=/usr/bin:/bin make install; \
    rm -rf /tmp/libxml2.tar.xz /tmp/libxml2-2.9.14 \
      /opt/droid-ddk/compat/bin /opt/droid-ddk/compat/include \
      /opt/droid-ddk/compat/share /opt/droid-ddk/compat/lib/pkgconfig \
      /opt/droid-ddk/compat/lib/*.la

ENV LIBCLANG_PATH=/usr/lib/llvm-22/lib \
    HOSTCFLAGS=-I/usr/include/libdwarf \
    LD_LIBRARY_PATH=/opt/droid-ddk/compat/lib
