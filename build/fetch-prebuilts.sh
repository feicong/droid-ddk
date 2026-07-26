#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
#
# 从 GitHub Release 下载 Droid DDK 构建所需的 .tar.zst 预构建包。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAP_FILE="$PROJECT_ROOT/mapping.json"

REPOSITORY="${DROID_DDK_PREBUILTS_REPOSITORY:-feicong/droid-ddk}"
RELEASE_TAG="${DROID_DDK_PREBUILTS_RELEASE_TAG:-prebuilts-v1}"
PREBUILTS_DIR="${DROID_DDK_PREBUILTS_DIR:-$PROJECT_ROOT/prebuilts}"
BASE_URL="${DROID_DDK_PREBUILTS_BASE_URL:-}"
HOST_PLATFORM=""
TARGET=""
FETCH_KDIR_MIN=false
FETCH_ALL_RUST=false
FETCH_TARGET_RUST=""
declare -a RUST_VERSIONS=()

usage() {
    cat <<'EOF'
用法: build/fetch-prebuilts.sh [选项]

从 GitHub Release 的稳定 tag prebuilts-v1 下载资产，并还原 Dockerfile 使用的
prebuilts 目录布局。

选项:
  -t, --target <androidX-Y>   下载 src 与 kdir/<平台> 资产
  -p, --host-platform <平台>  linux-amd64 或 linux-arm64；下载 kdir 时必填
      --kdir-min              同时下载 kdir-min/<平台> 资产，需要 --target
      --all-rust              下载 mapping.json 中当前平台需要的全部 Rust 资产
      --target-rust <目标>    下载指定目标在 mapping.json 中使用的 Rust 资产
      --rust <版本>           下载指定 Rust 资产，可重复指定
      --repository <owner/repo>
                              Release 所在仓库，默认 feicong/droid-ddk
      --release-tag <tag>     Release tag，默认 prebuilts-v1
      --output <目录>          预构建目录，默认仓库根目录/prebuilts
      --base-url <URL>         覆盖 Release 下载根地址，便于镜像或离线校验
  -h, --help                  显示帮助

资产命名:
  src.<目标>.tar.zst
  kdir.<平台>.<目标>.tar.zst
  kdir-min.<平台>.<目标>.tar.zst
  rust.<版本>.tar.zst
EOF
}

fail() {
    echo "Error: $*" >&2
    exit 2
}

require_value() {
    local option="$1"
    local value="${2:-}"
    [[ -n "$value" ]] || fail "$option requires a value"
}

validate_host_platform() {
    case "$HOST_PLATFORM" in
        linux-amd64|linux-arm64) ;;
        *) fail "--host-platform must be linux-amd64 or linux-arm64" ;;
    esac
}

release_base_url() {
    if [[ -n "$BASE_URL" ]]; then
        printf '%s\n' "${BASE_URL%/}"
        return
    fi
    printf 'https://github.com/%s/releases/download/%s\n' "$REPOSITORY" "$RELEASE_TAG"
}

download_asset() {
    local asset="$1"
    local destination="$2"
    local url
    url="$(release_base_url)/$asset"

    mkdir -p "$(dirname "$destination")"
    if [[ -s "$destination" ]]; then
        echo "[+] 已存在: $destination"
        return
    fi

    local temporary="${destination}.part"
    rm -f "$temporary"
    echo "[+] 下载 $asset"
    if ! curl --fail --location --retry 3 --retry-all-errors \
        --connect-timeout 20 --output "$temporary" "$url"; then
        rm -f "$temporary"
        fail "下载失败: ${url}；请确认 Release tag ${RELEASE_TAG} 已发布资产 ${asset}"
    fi
    [[ -s "$temporary" ]] || {
        rm -f "$temporary"
        fail "下载结果为空: $url"
    }
    mv "$temporary" "$destination"
}

target_supports_platform() {
    jq -e --arg target "$TARGET" --arg platform "$HOST_PLATFORM" '
        any(.matrix[]; .android == $target and ((.platforms // []) | index($platform)))
    ' "$MAP_FILE" >/dev/null
}

add_rust_version() {
    local version="$1"
    local existing
    for existing in "${RUST_VERSIONS[@]-}"; do
        [[ "$existing" == "$version" ]] && return
    done
    RUST_VERSIONS+=("$version")
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            require_value "$1" "${2:-}"
            TARGET="$2"
            shift
            ;;
        -p|--host-platform)
            require_value "$1" "${2:-}"
            HOST_PLATFORM="$2"
            shift
            ;;
        --kdir-min)
            FETCH_KDIR_MIN=true
            ;;
        --all-rust)
            FETCH_ALL_RUST=true
            ;;
        --target-rust)
            require_value "$1" "${2:-}"
            FETCH_TARGET_RUST="$2"
            shift
            ;;
        --rust)
            require_value "$1" "${2:-}"
            add_rust_version "$2"
            shift
            ;;
        --repository)
            require_value "$1" "${2:-}"
            REPOSITORY="$2"
            shift
            ;;
        --release-tag)
            require_value "$1" "${2:-}"
            RELEASE_TAG="$2"
            shift
            ;;
        --output)
            require_value "$1" "${2:-}"
            PREBUILTS_DIR="$2"
            shift
            ;;
        --base-url)
            require_value "$1" "${2:-}"
            BASE_URL="$2"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "unknown option: $1"
            ;;
    esac
    shift
done

[[ -f "$MAP_FILE" ]] || fail "mapping.json not found: $MAP_FILE"
mkdir -p "$PREBUILTS_DIR"

if [[ -n "$TARGET" || "$FETCH_KDIR_MIN" == true || "$FETCH_ALL_RUST" == true || -n "$FETCH_TARGET_RUST" ]]; then
    [[ -n "$HOST_PLATFORM" ]] || fail "--host-platform is required"
    validate_host_platform
fi

if [[ -n "$TARGET" ]]; then
    target_supports_platform || fail "$TARGET is not supported on $HOST_PLATFORM"
    download_asset "src.${TARGET}.tar.zst" \
        "$PREBUILTS_DIR/src/src.${TARGET}.tar.zst"
    download_asset "kdir.${HOST_PLATFORM}.${TARGET}.tar.zst" \
        "$PREBUILTS_DIR/kdir/${HOST_PLATFORM}/kdir.${TARGET}.tar.zst"
fi

if [[ "$FETCH_KDIR_MIN" == true ]]; then
    [[ -n "$TARGET" ]] || fail "--kdir-min requires --target"
    download_asset "kdir-min.${HOST_PLATFORM}.${TARGET}.tar.zst" \
        "$PREBUILTS_DIR/kdir-min/${HOST_PLATFORM}/kdir.${TARGET}.tar.zst"
fi

if [[ "$FETCH_ALL_RUST" == true ]]; then
    while IFS= read -r version; do
        [[ -n "$version" ]] && add_rust_version "$version"
    done < <(jq -r --arg platform "$HOST_PLATFORM" '
        [.matrix[]
         | select((.platforms // []) | index($platform))
         | .rust // empty]
        | unique[]
    ' "$MAP_FILE")
fi

if [[ -n "$FETCH_TARGET_RUST" ]]; then
    if ! jq -e --arg target "$FETCH_TARGET_RUST" --arg platform "$HOST_PLATFORM" '
        any(.matrix[]; .android == $target and ((.platforms // []) | index($platform)))
    ' "$MAP_FILE" >/dev/null; then
        fail "$FETCH_TARGET_RUST is not supported on $HOST_PLATFORM"
    fi
    while IFS= read -r version; do
        [[ -n "$version" ]] && add_rust_version "$version"
    done < <(jq -r --arg target "$FETCH_TARGET_RUST" --arg platform "$HOST_PLATFORM" '
        [.matrix[]
         | select(.android == $target and ((.platforms // []) | index($platform)))
         | .rust // empty]
        | unique[]
    ' "$MAP_FILE")
fi

for version in "${RUST_VERSIONS[@]-}"; do
    [[ -n "$version" ]] || continue
    download_asset "rust.${version}.tar.zst" \
        "$PREBUILTS_DIR/rust/${version}.tar.zst"
done

if [[ -z "$TARGET" && -z "$FETCH_TARGET_RUST" && -z "${RUST_VERSIONS[*]-}" ]]; then
    fail "select --target and/or --all-rust/--rust"
fi

echo "[+] 预构建包已就绪: $PREBUILTS_DIR"
