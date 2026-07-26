# Droid DDK 镜像构建

本仓库按 ACK 版本构建 ARM64 Android 内核开发镜像，构建容器统一使用 Ubuntu 26.04。

| `VER` | NDK |
|---|---|
| `android14-5.15` | r25c |
| `android14-6.1` | r25c |
| `android15-6.6` | r25c |
| `android16-6.12` | r29 |
| `android17-6.18` | r29 |

ARM64 Linux 宿主机使用 SnowNF ARM64 NDK，x86_64 Linux 宿主机使用 Google 官方 x86_64 NDK。`docker/Makefile` 根据当前宿主架构自动选择对应工具链和 `kdir`。

## 准备仓库

```bash
git clone --recurse-submodules https://github.com/feicong/droid-ddk.git
cd droid-ddk
git lfs install
git submodule update --init --recursive
```

拉取某个版本的源码、当前宿主平台 `kdir`，以及 Android 16/17 使用的 Rust 预构建包：

```bash
VER=android17-6.18
HOST_PLATFORM=linux-arm64   # x86_64 宿主机填写 linux-amd64

git -C prebuilts lfs pull --include="src/src.${VER}.tar.zst"
git -C prebuilts lfs pull --include="kdir/${HOST_PLATFORM}/kdir.${VER}.tar.zst"
git -C prebuilts lfs pull --include="rust/**"
```

## 构建单个版本

```bash
VER=android17-6.18

make -C docker builder
make -C docker toolchains VER="$VER"
make -C docker build VER="$VER"
```

生成的镜像为：

```text
docker.io/fsx199/droid-ddk-toolchain:android17-6.18
docker.io/fsx199/droid-ddk:android17-6.18
```

精简镜像使用对应的 `prebuilts/kdir-min/<host-platform>` 产物：

```bash
make -C docker build-min VER="$VER"
```

## 使用镜像编译外部内核模块

使用完整的`droid-ddk`镜像。镜像内`/kernel/out`包含与镜像版本匹配的内核构建目录、`Module.symvers`和`modpost`，`/kernel/src`指向对应内核源码。

模块目录至少需要模块源码和`Makefile`。例如`my-driver/Makefile`：

```make
obj-m += my_driver.o
```

选择与目标设备内核一致的镜像并构建模块：

```bash
VER=android17-6.18
IMAGE="docker.io/fsx199/droid-ddk:${VER}"
MODULE_DIR="$PWD/my-driver"

docker run --rm --platform linux/arm64 \
    --user "$(id -u):$(id -g)" \
    -v "${MODULE_DIR}:/module" \
    -w /module \
    "${IMAGE}" \
    make -C /kernel/out M=/module modules
```

构建产物写入`$MODULE_DIR`。检查模块架构和与目标内核匹配的`vermagic`：

```bash
file "$MODULE_DIR/my_driver.ko"

docker run --rm --platform linux/arm64 \
    -v "${MODULE_DIR}:/module:ro" \
    "${IMAGE}" \
    modinfo -F vermagic /module/my_driver.ko
```

清理模块构建产物：

```bash
docker run --rm --platform linux/arm64 \
    --user "$(id -u):$(id -g)" \
    -v "${MODULE_DIR}:/module" \
    -w /module \
    "${IMAGE}" \
    make -C /kernel/out M=/module clean
```

### 使用`dddk`管理模块构建

在 Linux 宿主机执行`host/install.sh`后，`dddk`安装到`/usr/local/bin/dddk`。未安装时可以用`./scripts/dddk`替代下列命令。首次运行时选择`docker`模式和`docker`镜像源。

`--module`会将模块目录挂载为`/build`，并自动执行`make -C /kernel/out M=/build`。构建产物按当前宿主用户写入模块目录：

```bash
VER=android17-6.18
MODULE_DIR="$PWD/my-driver"

dddk pull --target "$VER"
dddk build --target "$VER" --module "$MODULE_DIR"
dddk build --target "$VER" --module "$MODULE_DIR" -- -j8 V=1
dddk clean --target "$VER" --module "$MODULE_DIR"
```

命令未指定`--target`时，`dddk`依次读取`.droid-ddk-version`和`DROID_DDK_TARGET`。`--`之后的参数会原样传给`make`。

## 构建不同版本

修改 `VER` 即可逐个构建：

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

也可以一次构建当前宿主平台支持的全部版本：

```bash
make -C docker toolchains
make -C docker build-all
```

## 推送镜像

先完成 `docker login`，再设置 `PUSH=1`：

```bash
VER=android17-6.18
make -C docker builder PUSH=1
make -C docker toolchains VER="$VER" PUSH=1
make -C docker build VER="$VER" PUSH=1
```

默认仓库命名空间是 `docker.io/fsx199`，通过 `REG` 可指定其他仓库。
