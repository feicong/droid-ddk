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
| `android17-6.12` | `android16-6.12-lts` | r29 |
| `android17-6.18` | `android17-6.18-lts` | r29 |

`android15-6.1`、`android16-6.6`与`android17-6.12`用于在较新Android系统上继续匹配上一代ACK内核。选择目标时以设备`uname -r`中的ACK代际和内核版本为准。

## 安装`dddk`

```bash
curl -fsSL https://raw.githubusercontent.com/feicong/droid-ddk/main/host/install.sh | sudo bash
```

首次运行会在当前项目目录生成`.dddk-config`。镜像同时发布到DockerHub的`docker.io/fsx199/droid-ddk`与GHCR的`ghcr.io/feicong/droid-ddk`；镜像源选择`docker`或`github`即可，`dddk`会按宿主架构自动拉取x86_64或ARM64镜像。

也可直接创建项目配置：

```ini
version=android17-6.18
mode=docker
source=github
slim=true
```

`.dddk-config`必须同时包含`version`、`mode`和`source`。`version`使用`android<主版本>-<内核版本>`格式，`mode`接受`docker`或`local`，`source`接受`docker`、`github`或`cnb`。可选的`slim=true`选择同一目标的`droid-ddk-min`精简镜像；省略或设为`false`时使用完整镜像。`dddk`逐项解析该文件，不执行其中的Shell内容，也不读取或写入`$HOME/.droid-ddk/source`与`$HOME/.droid-ddk/mode`。

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

项目用`.dddk-config`固定默认目标：

```bash
dddk pull
dddk build --module "$PWD/my-driver" -- -j8
dddk clean --module "$PWD/my-driver"
```

命令行`--target`优先级高于`.dddk-config`中的`version`。省略`--platform`时，`dddk`按当前宿主自动选择`linux/amd64`或`linux/arm64`；只有覆盖宿主判断时才显式传入平台。

## 在GitHub Actions中编译

`feicong/android-kernel-build-action@v2`使用`dddk`编译ARM64外部内核模块。先上传模块源码Artifact，再调用Action：

```yaml
jobs:
  upload-module:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v6
      - uses: actions/upload-artifact@v7
        with:
          name: hello-ko
          path: path/to/hello-ko

  build-module:
    needs: upload-module
    runs-on: ubuntu-24.04
    steps:
      - uses: feicong/android-kernel-build-action@v2
        with:
          tag: android17-6.18
          arch: aarch64
          module-path: hello-ko
          module-name: hello-ko
          registry: ghcr
```

模块目录需包含`Makefile`与同名`.c`文件。输出Artifact名为`Image-TAG-ARCH`，其中的模块文件名为`TAG_MODULE_NAME.ko`。

## 致谢

项目fork自Ylarod/ddk。
