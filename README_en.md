# Droid DDK - dddk

`droid-ddk` provides Android ACK external kernel module build images. x86_64 hosts use the official Google x86_64 NDK, ARM64 hosts use the SnowNF ARM64 NDK, and all images use Ubuntu 26.04.

| `dddk` target | ACK source branch | NDK |
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

`android15-6.1`, `android16-6.6`, and `android17-6.12` keep the previous ACK generation available for newer Android releases. Select a target that matches the ACK generation and kernel version reported by the device's `uname -r`.

## Install `dddk`

```bash
curl -fsSL https://raw.githubusercontent.com/feicong/droid-ddk/main/host/install.sh | sudo bash
```

On first use, `dddk` creates `.dddk-config` in the current project directory. Images are published to both `docker.io/fsx199/droid-ddk` and `ghcr.io/feicong/droid-ddk`. Select the `docker` or `github` source; `dddk` automatically pulls the x86_64 or ARM64 image for the host architecture.

The project configuration can also be created directly:

```ini
version=android17-6.18
mode=docker
source=github
slim=true
```

`.dddk-config` must contain `version`, `mode`, and `source`. `version` uses the `android<major>-<kernel>` format, `mode` accepts `docker` or `local`, and `source` accepts `docker`, `github`, or `cnb`. Optional `slim=true` selects the target's reduced `droid-ddk-min` image; omitting it or setting it to `false` selects the full image. `dddk` parses the fields without executing shell content and does not read or write `$HOME/.droid-ddk/source` or `$HOME/.droid-ddk/mode`.

```bash
dddk update
dddk list-all
dddk pull --target android17-6.18
dddk list
```

## Build a Kernel Module

The module directory must contain its source and a Kbuild-compatible Makefile. For example:

```makefile
obj-m += my_driver.o
```

Use the full image to build, clean, or open the build environment:

```bash
MODULE_DIR="$PWD/my-driver"
TARGET=android17-6.18

dddk pull --target "$TARGET"
dddk build --target "$TARGET" --module "$MODULE_DIR"
dddk build --target "$TARGET" --module "$MODULE_DIR" -- -j8 V=1
dddk clean --target "$TARGET" --module "$MODULE_DIR"
dddk shell --target "$TARGET" --module "$MODULE_DIR"
```

`--module` mounts the module directory at `/build` and runs the standard Kbuild command against the matching kernel build directory. The `.ko` file and intermediate outputs are written directly to the module directory.

Pin the default target in `.dddk-config`:

```bash
dddk pull
dddk build --module "$PWD/my-driver" -- -j8
dddk clean --module "$PWD/my-driver"
```

`--target` takes precedence over `version` in `.dddk-config`. Without `--platform`, `dddk` selects `linux/amd64` or `linux/arm64` from the current host. Pass a platform only to override host detection. Set `DDK_ROOT` to override the local DDK installation path.

## Build in GitHub Actions

`feicong/android-kernel-build-action@v2` uses `dddk` to build ARM64 external kernel modules. Upload the module source artifact, then invoke the action:

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

The module directory must contain a `Makefile` and a matching `.c` file. The output artifact is named `Image-TAG-ARCH` and contains `TAG_MODULE_NAME.ko`.

## Credits

Forked from Ylarod/ddk.
