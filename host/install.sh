#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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
    [[ "$(uname -s)" == Linux ]] || {
        printf 'dddk仅支持Linux宿主机\n' >&2
        exit 2
    }
    install_dddk
}

main "$@"
