# Droid DDK Docker 镜像

构建环境统一基于 Ubuntu 26.04。正式镜像包括：

| 镜像 | 说明 |
|---|---|
| `droid-ddk-builder` | 基础内核构建环境 |
| `droid-ddk-toolchain` | 宿主架构对应的 NDK 与 Rust 工具链 |
| `droid-ddk` | 内核源码与完整 kdir |
| `droid-ddk-min` | 内核源码与精简 kdir |

ARM64 Linux 宿主机下载 SnowNF ARM64 NDK，x86_64 Linux 宿主机下载 Google 官方 x86_64 NDK。Android 14、15 使用 r25c，Android 16、17 使用 r29。

```bash
make -C docker list
make -C docker builder
make -C docker toolchains
make -C docker build VER=android17-6.18
make -C docker build-min VER=android17-6.18
```

默认仓库为 `docker.io/fsx199`。推送镜像时设置 `PUSH=1`：

```bash
make -C docker toolchains PUSH=1
make -C docker build VER=android17-6.18 PUSH=1
```

`PLAT=linux/arm64` 对应 `linux-arm64` 产物，`PLAT=linux/amd64` 对应 `linux-amd64` 产物。平台值应与执行构建的宿主架构一致。
