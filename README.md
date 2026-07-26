# Droid DDK - dddk

`droid-ddk`提供Android ACK外部内核模块编译镜像。x86_64宿主机自动使用Google官方x86_64 NDK，ARM64宿主机自动使用SnowNF ARM64 NDK，镜像构建环境为Ubuntu 26.04。

| `dddk`目标 | ACK源码分支 | NDK |
|---|---|---|
| `android13-5.15` | `android13-5.15-lts` | r25c |
| `android14-5.15` | `android14-5.15-lts` | r25c |
| `android14-6.1` | `android14-6.1-lts` | r25c |
| `android15-6.1` | `android14-6.1-lts` | r25c |
| `android15-6.6` | `android15-6.6-lts` | r25c |
| `android16-6.6` | `android15-6.6-lts` | r25c |
| `android16-6.12` | `android16-6.12-lts` | r29 |
| `android17-6.18` | `android17-6.18-lts` | r29 |

`android15-6.1`与`android16-6.6`用于在较新Android系统上继续匹配上一代ACK内核。选择目标时以设备`uname -r`中的ACK代际和内核版本为准。

## 安装`dddk`

```bash
curl -fsSL https://raw.githubusercontent.com/feicong/droid-ddk/main/host/install.sh | sudo bash
```

首次运行选择`docker`模式。镜像同时发布到Docker Hub的`docker.io/fsx199/droid-ddk`与GHCR的`ghcr.io/feicong/droid-ddk`；镜像源选择`docker`或`github`即可，`dddk`会按宿主架构自动拉取x86_64或ARM64镜像。

```bash
dddk update
dddk list-all
dddk pull --target android17-6.18
dddk list
```

## 编译内核模块

模块目录至少包含模块源码和Kbuild文件。例如：

```makefile
obj-m += my_driver.o
```

使用完整镜像编译、清理和进入构建环境：

```bash
MODULE_DIR="$PWD/my-driver"
TARGET=android17-6.18

dddk pull --target "$TARGET"
dddk build --target "$TARGET" --module "$MODULE_DIR"
dddk build --target "$TARGET" --module "$MODULE_DIR" -- -j8 V=1
dddk clean --target "$TARGET" --module "$MODULE_DIR"
dddk shell --target "$TARGET" --module "$MODULE_DIR"
```

`--module`将模块目录挂载到镜像内的`/build`，并执行与镜像内核构建目录匹配的标准Kbuild命令。`.ko`及中间产物直接写入模块目录。

项目可用`.droid-ddk-version`固定默认目标：

```bash
echo android17-6.18 > .droid-ddk-version
dddk pull
dddk build --module "$PWD/my-driver" -- -j8
dddk clean --module "$PWD/my-driver"
```

命令行`--target`优先级高于`.droid-ddk-version`，后者优先级高于`DROID_DDK_TARGET`环境变量。通过`--platform linux/amd64`或`--platform linux/arm64`可以显式选择镜像架构。

## 致谢

项目fork自Ylarod/ddk。
