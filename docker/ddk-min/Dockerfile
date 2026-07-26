# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

ARG TOOLCHAIN_IMAGE=docker.io/fsx199/droid-ddk-toolchain:latest
FROM ${TOOLCHAIN_IMAGE}

WORKDIR /opt/droid-ddk

ARG TARGETARCH
ARG ANDROID_VER
ARG CLANG_VER
ARG RUST_VER
ARG VERSION="${ANDROID_VER}"
ARG REVISION
ARG CREATED
ARG REPOSITORY="https://github.com/feicong/droid-ddk"
ARG HOMEPAGE="https://github.com/feicong/droid-ddk"
ARG DOCUMENTATION="https://github.com/feicong/droid-ddk#readme"
ARG LICENSE="Apache-2.0"
ARG VENDOR="feicong"

LABEL org.opencontainers.image.title="Droid DDK-min ${ANDROID_VER}" \
      org.opencontainers.image.description="Minimal Kernel Driver Development Kit for ${ANDROID_VER}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.url="${HOMEPAGE}" \
      org.opencontainers.image.source="${REPOSITORY}" \
      org.opencontainers.image.documentation="${DOCUMENTATION}" \
      org.opencontainers.image.licenses="${LICENSE}" \
      org.opencontainers.image.vendor="${VENDOR}" \
      io.droid-ddk.project="droid-ddk" \
      io.droid-ddk.variant="min" \
      io.droid-ddk.android.version="${ANDROID_VER}" \
      io.droid-ddk.clang.reference="${CLANG_VER}" \
      io.droid-ddk.rust.version="${RUST_VER}" \
      io.droid-ddk.kernel.src="${ANDROID_VER}"

RUN --mount=type=bind,source=prebuilts,target=/mnt/prebuilts,readonly \
    set -eux; \
    artifact_platform="linux-${TARGETARCH}"; \
    kernel_src="/opt/droid-ddk/src/${ANDROID_VER}"; \
    kernel_out="/opt/droid-ddk/kdir/${artifact_platform}/${ANDROID_VER}"; \
    mkdir -p "/opt/droid-ddk/src" "/opt/droid-ddk/kdir/${artifact_platform}" /kernel; \
    tar -xf "/mnt/prebuilts/src/src.${ANDROID_VER}.tar.zst" -C /opt/droid-ddk/src; \
    tar -xf "/mnt/prebuilts/kdir-min/${artifact_platform}/kdir.${ANDROID_VER}.tar.zst" -C "/opt/droid-ddk/kdir/${artifact_platform}"; \
    ln -s "$kernel_src" /kernel/src; \
    ln -s "$kernel_out" /kernel/out; \
    recorded_src="$(sed -n 's|^include \(.*\)/Makefile$|\1|p' "$kernel_out/Makefile")"; \
    test -n "$recorded_src"; \
    case "$recorded_src" in /*) ;; *) exit 2 ;; esac; \
    if [ "$recorded_src" != "$kernel_src" ]; then \
      test ! -e "$recorded_src"; \
      test ! -L "$recorded_src"; \
      mkdir -p "$(dirname "$recorded_src")"; \
      ln -s "$kernel_src" "$recorded_src"; \
    fi; \
    recorded_out="$(sed -n 's|^export KBUILD_OUTPUT[[:space:]]*=[[:space:]]*||p' "$kernel_out/Makefile")"; \
    if [ -n "$recorded_out" ] && [ "$recorded_out" != "$kernel_out" ]; then \
      case "$recorded_out" in /*) ;; *) exit 2 ;; esac; \
      test ! -e "$recorded_out"; \
      test ! -L "$recorded_out"; \
      mkdir -p "$(dirname "$recorded_out")"; \
      ln -s "$kernel_out" "$recorded_out"; \
    fi

ENV DDK_ROOT=/opt/droid-ddk \
    CROSS_COMPILE=aarch64-linux-gnu- \
    ARCH=arm64 \
    LLVM=1 \
    LLVM_IAS=1 \
    KERNEL_SRC=/opt/droid-ddk/src/${ANDROID_VER} \
    KDIR=/opt/droid-ddk/kdir/linux-${TARGETARCH}/${ANDROID_VER} \
    CLANG_PATH=/opt/droid-ddk/toolchain/bin \
    PATH=/opt/droid-ddk/toolchain/bin:/opt/droid-ddk/.cargo/bin:$PATH

CMD ["/bin/bash"]
