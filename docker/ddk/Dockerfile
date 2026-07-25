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
ARG ISSUES="https://github.com/feicong/droid-ddk/issues"
ARG LICENSE="Apache-2.0"
ARG VENDOR="feicong"

LABEL org.opencontainers.image.title="Droid DDK ${ANDROID_VER}" \
      org.opencontainers.image.description="Kernel Driver Development Kit for ${ANDROID_VER} (offline build)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.url="${HOMEPAGE}" \
      org.opencontainers.image.source="${REPOSITORY}" \
      org.opencontainers.image.documentation="${DOCUMENTATION}" \
      org.opencontainers.image.licenses="${LICENSE}" \
      org.opencontainers.image.vendor="${VENDOR}" \
      io.droid-ddk.project="droid-ddk" \
      io.droid-ddk.android.version="${ANDROID_VER}" \
      io.droid-ddk.clang.reference="${CLANG_VER}" \
      io.droid-ddk.rust.version="${RUST_VER}" \
      io.droid-ddk.kernel.src="${ANDROID_VER}"

RUN --mount=type=bind,source=prebuilts,target=/mnt/prebuilts,readonly \
    set -eux; \
    artifact_platform="linux-${TARGETARCH}"; \
    mkdir -p "/opt/droid-ddk/src" "/opt/droid-ddk/kdir/${artifact_platform}" /kernel; \
    tar -xf "/mnt/prebuilts/src/src.${ANDROID_VER}.tar.zst" -C /opt/droid-ddk/src; \
    tar -xf "/mnt/prebuilts/kdir/${artifact_platform}/kdir.${ANDROID_VER}.tar.zst" -C "/opt/droid-ddk/kdir/${artifact_platform}"; \
    ln -s "/opt/droid-ddk/src/${ANDROID_VER}" /kernel/src; \
    ln -s "/opt/droid-ddk/kdir/${artifact_platform}/${ANDROID_VER}" /kernel/out

ENV DROID_DDK_ROOT=/opt/droid-ddk \
    CROSS_COMPILE=aarch64-linux-gnu- \
    ARCH=arm64 \
    LLVM=1 \
    LLVM_IAS=1 \
    KERNEL_SRC=/opt/droid-ddk/kdir/linux-${TARGETARCH}/${ANDROID_VER} \
    KDIR=/opt/droid-ddk/kdir/linux-${TARGETARCH}/${ANDROID_VER} \
    CLANG_PATH=/opt/droid-ddk/toolchain/bin \
    PATH=/opt/droid-ddk/toolchain/bin:/opt/droid-ddk/.cargo/bin:$PATH

CMD ["/bin/bash"]
