#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

REPOSITORY="${DROID_DDK_REPOSITORY:-feicong/droid-ddk}"
REF="${DROID_DDK_REF:-main}"
RAW_BASE="${DROID_DDK_RAW_BASE:-https://raw.githubusercontent.com/$REPOSITORY/$REF}"

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        printf '缺少命令：%s\n' "$1" >&2
        exit 1
    }
}

install_dddk() {
    local bin_dir="${DROID_DDK_BIN_DIR:-/usr/local/bin}"
    local download_dir
    download_dir=$(mktemp -d)
    trap 'rm -rf "$download_dir"' EXIT

    curl --fail --silent --show-error --location --retry 3 --retry-all-errors \
        --output "$download_dir/dddk" "$RAW_BASE/scripts/dddk"
    if [[ "$EUID" -eq 0 ]]; then
        install -d -m 0755 "$bin_dir"
        install -m 0755 "$download_dir/dddk" "$bin_dir/dddk"
    else
        require_command sudo
        sudo install -d -m 0755 "$bin_dir"
        sudo install -m 0755 "$download_dir/dddk" "$bin_dir/dddk"
    fi

    printf '[+] 已安装命令：%s/dddk\n' "$bin_dir"
    rm -rf "$download_dir"
    trap - EXIT
}

main() {
    [[ "$(uname -s)" == Linux ]] || {
        printf 'dddk仅支持Linux宿主机\n' >&2
        exit 2
    }
    require_command curl
    require_command install
    require_command mktemp
    install_dddk
}

main "$@"
