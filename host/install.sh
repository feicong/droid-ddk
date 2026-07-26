#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DROID_DDK_ROOT="${DROID_DDK_ROOT:-/opt/droid-ddk}"
MAPPING_FILE="${MAPPING_FILE:-$PROJECT_ROOT/mapping.json}"

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf '缺少命令：%s\n' "$1" >&2
        exit 1
    fi
}

detect_host_platform() {
    case "$(uname -m)" in
        x86_64|amd64)
            printf '%s\n' linux-amd64
            ;;
        aarch64|arm64)
            printf '%s\n' linux-arm64
            ;;
        *)
            printf '不支持的Linux宿主架构：%s\n' "$(uname -m)" >&2
            exit 2
            ;;
    esac
}

extract_kdir() {
    local host_platform="$1"
    local source_dir="$PROJECT_ROOT/prebuilts/kdir/$host_platform"
    local destination="$DROID_DDK_ROOT/kdir/$host_platform"
    local archive
    local found=false

    mkdir -p "$destination"
    for archive in "$source_dir"/*.tar.zst; do
        [[ -f "$archive" ]] || continue
        found=true
        printf '[+] 解压 %s\n' "$archive"
        tar -xf "$archive" -C "$destination"
    done
    if [[ "$found" == false ]]; then
        printf '未找到kdir归档：%s\n' "$source_dir" >&2
        exit 1
    fi
}

install_dddk() {
    local bin_dir="${DROID_DDK_BIN_DIR:-/usr/local/bin}"
    local lib_dir="${DROID_DDK_LIB_DIR:-/usr/local/lib/droid-ddk}"
    local bin_parent lib_parent
    bin_parent=$(dirname "$bin_dir")
    lib_parent=$(dirname "$lib_dir")

    if [[ -w "$bin_parent" && -w "$lib_parent" ]]; then
        install -d -m 0755 "$bin_dir" "$lib_dir"
        install -m 0755 "$PROJECT_ROOT/scripts/dddk" "$bin_dir/dddk"
        install -m 0755 "$PROJECT_ROOT/scripts/lib/platform.sh" "$lib_dir/platform.sh"
    else
        sudo install -d -m 0755 "$bin_dir" "$lib_dir"
        sudo install -m 0755 "$PROJECT_ROOT/scripts/dddk" "$bin_dir/dddk"
        sudo install -m 0755 "$PROJECT_ROOT/scripts/lib/platform.sh" "$lib_dir/platform.sh"
    fi

    printf '[+] 已安装命令：%s/dddk\n' "$bin_dir"
}

main() {
    require_command python3
    require_command curl
    require_command tar
    require_command zstd
    [[ "$(uname -s)" == Linux ]] || {
        printf 'Host模式仅支持Linux\n' >&2
        exit 2
    }

    local host_platform
    host_platform=$(detect_host_platform)
    export DROID_DDK_ROOT

    python3 "$PROJECT_ROOT/build/build-droid-ddk.py" setup-toolchain \
        --source prebuilt \
        --host-platform "$host_platform" \
        --map-file "$MAPPING_FILE"
    python3 "$PROJECT_ROOT/build/build-droid-ddk.py" setup-src \
        --source prebuilt \
        --host-platform "$host_platform" \
        --map-file "$MAPPING_FILE"
    extract_kdir "$host_platform"
    install_dddk

    printf '[+] Droid DDK安装目录：%s\n' "$DROID_DDK_ROOT"
}

main "$@"
