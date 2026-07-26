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
| `android17-6.18` | `android17-6.18-lts` | r29 |

`android15-6.1` and `android16-6.6` keep the previous ACK generation available for newer Android releases. Select a target that matches the ACK generation and kernel version reported by the device's `uname -r`.

## Install `dddk`

```bash
curl -fsSL https://raw.githubusercontent.com/feicong/droid-ddk/main/host/install.sh | sudo bash
```

Select `docker` mode on first use. Images are published to both `docker.io/fsx199/droid-ddk` and `ghcr.io/feicong/droid-ddk`. Select the `docker` or `github` source; `dddk` automatically pulls the x86_64 or ARM64 image for the host architecture.

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

Pin the default target with `.ddk-version`:

```bash
echo android17-6.18 > .ddk-version
dddk pull
dddk build --module "$PWD/my-driver" -- -j8
dddk clean --module "$PWD/my-driver"
```

`--target` takes precedence over `.ddk-version`, which takes precedence over the `DDK_TARGET` environment variable. Set `DDK_ROOT` to override the local DDK installation path. Use `--platform linux/amd64` or `--platform linux/arm64` to select an image architecture explicitly.

## Credits

Forked from Ylarod/ddk.
