# Droid DDK Image Builds

This repository builds ARM64 Android kernel development images by ACK version. All build containers use Ubuntu 26.04.

| `VER` | NDK |
|---|---|
| `android14-5.15` | r25c |
| `android14-6.1` | r25c |
| `android15-6.6` | r25c |
| `android16-6.12` | r29 |
| `android17-6.18` | r29 |

ARM64 Linux hosts use the SnowNF ARM64 NDK. x86_64 Linux hosts use the official Google x86_64 NDK. `docker/Makefile` selects the toolchain and `kdir` for the current host architecture.

## Prepare the Repository

```bash
git clone --recurse-submodules https://github.com/feicong/droid-ddk.git
cd droid-ddk
git lfs install
git submodule update --init --recursive
```

Pull the source, the current host platform's `kdir`, and the Rust prebuilts used by Android 16 and 17:

```bash
VER=android17-6.18
HOST_PLATFORM=linux-arm64   # Use linux-amd64 on an x86_64 host

git -C prebuilts lfs pull --include="src/src.${VER}.tar.zst"
git -C prebuilts lfs pull --include="kdir/${HOST_PLATFORM}/kdir.${VER}.tar.zst"
git -C prebuilts lfs pull --include="rust/**"
```

## Build One Version

```bash
VER=android17-6.18

make -C docker builder
make -C docker toolchains VER="$VER"
make -C docker build VER="$VER"
```

The resulting images are:

```text
docker.io/fsx199/droid-ddk-toolchain:android17-6.18
docker.io/fsx199/droid-ddk:android17-6.18
```

The minimal image uses the matching `prebuilts/kdir-min/<host-platform>` artifact:

```bash
make -C docker build-min VER="$VER"
```

## Build Different Versions

Change `VER` to build each supported release:

```bash
for VER in \
    android14-5.15 \
    android14-6.1 \
    android15-6.6 \
    android16-6.12 \
    android17-6.18
do
    make -C docker toolchains VER="$VER"
    make -C docker build VER="$VER"
done
```

Build every version supported by the current host platform with:

```bash
make -C docker toolchains
make -C docker build-all
```

## Push Images

Run `docker login`, then set `PUSH=1`:

```bash
VER=android17-6.18
make -C docker builder PUSH=1
make -C docker toolchains VER="$VER" PUSH=1
make -C docker build VER="$VER" PUSH=1
```

The default registry namespace is `docker.io/fsx199`. Set `REG` to use another registry.
