# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

ARG BUILDER_IMAGE=docker.io/fsx199/droid-ddk-builder:latest
FROM ${BUILDER_IMAGE}

WORKDIR /opt/droid-ddk

ARG TARGETARCH
ARG CLANG_VER
ARG RUST_VER=""
ARG BINDGEN_VER=0.72.1
ARG NDK_VERSION=r29
ARG NDK_URL=https://github.com/SnowNF/ndk-aarch64-linux/releases/download/0.0.2/android-ndk-r29-linux-aarch64.tar.gz
ARG NDK_SHA256=48cb104c28e1ede5e1884b0b34d97d28c4df74cd4e8f7628202a4c2c8de78a50
ARG NDK_ROOT=r29

ENV DROID_DDK_ROOT=/opt/droid-ddk \
    RUSTUP_HOME=/opt/droid-ddk/.rustup \
    CARGO_HOME=/opt/droid-ddk/.cargo \
    RUSTUP_NO_SELF_UPDATE=1 \
    LIBCLANG_PATH=/usr/lib/llvm-22/lib \
    PATH=/opt/droid-ddk/toolchain/bin:/opt/droid-ddk/.cargo/bin:$PATH

RUN --mount=type=bind,source=prebuilts,target=/mnt/prebuilts,readonly \
    set -eux; \
    case "$TARGETARCH" in \
      amd64) \
        test -f "/mnt/prebuilts/clang/${CLANG_VER}.tar.zst"; \
        mkdir -p /opt/droid-ddk/clang; \
        tar -I zstd -xf "/mnt/prebuilts/clang/${CLANG_VER}.tar.zst" -C /opt/droid-ddk/clang; \
        toolchain_bin="/opt/droid-ddk/clang/${CLANG_VER}/bin"; \
        if [ -n "$RUST_VER" ]; then \
          test -f "/mnt/prebuilts/rust/${RUST_VER}.tar.zst"; \
          mkdir -p /opt/droid-ddk/rust; \
          tar -I zstd -xf "/mnt/prebuilts/rust/${RUST_VER}.tar.zst" -C /opt/droid-ddk/rust; \
        fi ;; \
      arm64) \
        curl -fsSL "$NDK_URL" -o /tmp/droid-ddk-ndk.tar.gz; \
        echo "$NDK_SHA256  /tmp/droid-ddk-ndk.tar.gz" | sha256sum -c -; \
        mkdir -p /opt/droid-ddk/ndk; \
        tar -xzf /tmp/droid-ddk-ndk.tar.gz -C /opt/droid-ddk/ndk; \
        rm -f /tmp/droid-ddk-ndk.tar.gz; \
        toolchain_bin="/opt/droid-ddk/ndk/${NDK_ROOT}/toolchains/llvm/prebuilt/linux-x86_64/bin"; \
        if [ -n "$RUST_VER" ]; then \
          rust_version="${RUST_VER#rust-}"; \
          curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs | sh -s -- -y --no-modify-path --default-toolchain none; \
          /opt/droid-ddk/.cargo/bin/rustup toolchain install "$rust_version" --profile minimal --component rust-src,rustfmt; \
          /opt/droid-ddk/.cargo/bin/rustup default "$rust_version"; \
          /opt/droid-ddk/.cargo/bin/cargo "+${rust_version}" install bindgen-cli --version "$BINDGEN_VER" --locked; \
        fi ;; \
      *) echo "Unsupported TARGETARCH: $TARGETARCH" >&2; exit 2 ;; \
    esac; \
    test -x "$toolchain_bin/clang"; \
    mkdir -p /opt/droid-ddk/toolchain; \
    ln -s "$toolchain_bin" /opt/droid-ddk/toolchain/bin

RUN if [ "$TARGETARCH" = "arm64" ] && [ -n "$RUST_VER" ]; then \
      mkdir -p /opt/droid-ddk/bin; \
      printf '%s\n' '#!/bin/sh' 'unset CLANG_PATH' 'exec /opt/droid-ddk/.cargo/bin/bindgen "$@"' > /opt/droid-ddk/bin/bindgen; \
      chmod 0755 /opt/droid-ddk/bin/bindgen; \
    fi

ENV CLANG_PATH=/opt/droid-ddk/toolchain/bin \
    CROSS_COMPILE=aarch64-linux-gnu- \
    ARCH=arm64 \
    LLVM=1 \
    LLVM_IAS=1 \
    PATH=/opt/droid-ddk/bin:/opt/droid-ddk/toolchain/bin:/opt/droid-ddk/.cargo/bin:$PATH

LABEL org.opencontainers.image.title="Droid DDK toolchain ${CLANG_VER}" \
      org.opencontainers.image.description="Droid DDK toolchain base image" \
      org.opencontainers.image.source="https://github.com/feicong/droid-ddk" \
      org.opencontainers.image.documentation="https://github.com/feicong/droid-ddk#readme" \
      org.opencontainers.image.url="https://github.com/feicong/droid-ddk" \
      io.droid-ddk.project="droid-ddk" \
      io.droid-ddk.clang.reference="${CLANG_VER}" \
      io.droid-ddk.rust.version="${RUST_VER}" \
      io.droid-ddk.ndk.version="${NDK_VERSION}"

CMD ["/bin/bash"]
