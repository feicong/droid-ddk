#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
#
# 将本地 prebuilts 目录中的 .tar.zst 包发布到 GitHub Release。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAP_FILE="$PROJECT_ROOT/mapping.json"

REPOSITORY="${DROID_DDK_PREBUILTS_REPOSITORY:-feicong/droid-ddk}"
RELEASE_TAG="${DROID_DDK_PREBUILTS_RELEASE_TAG:-prebuilts-v1}"
PREBUILTS_DIR="${DROID_DDK_PREBUILTS_DIR:-$PROJECT_ROOT/prebuilts}"
TARGET=""
HOST_PLATFORM=""
INCLUDE_KDIR_MIN=false
INCLUDE_TARGET_RUST=false
INCLUDE_ALL_RUST=false
DRY_RUN=false

usage() {
    cat <<'EOF'
用法: build/publish-prebuilts.sh --target <androidX-Y> --host-platform <平台> [选项]

将 pack-droid-ddk.sh 生成的本地 .tar.zst 上传到 GitHub Release。默认 Release
tag 为 prebuilts-v1；同名资产会被覆盖，供 fetch-prebuilts.sh 稳定下载。

选项:
  -t, --target <androidX-Y>   必填；上传 src 与 kdir/<平台>
  -p, --host-platform <平台>  必填；linux-amd64 或 linux-arm64
      --kdir-min              同时上传 kdir-min/<平台>
      --rust                  上传该目标在 mapping.json 中使用的 Rust 资产
      --all-rust              上传当前平台使用的全部 Rust 资产
      --repository <owner/repo>
                              Release 所在仓库，默认 feicong/droid-ddk
      --release-tag <tag>     Release tag，默认 prebuilts-v1
      --input <目录>           预构建目录，默认仓库根目录/prebuilts
      --dry-run                只校验路径并打印上传计划
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

target_supports_platform() {
    jq -e --arg target "$TARGET" --arg platform "$HOST_PLATFORM" '
        any(.matrix[]; .android == $target and ((.platforms // []) | index($platform)))
    ' "$MAP_FILE" >/dev/null
}

declare -a UPLOAD_PATHS=()
declare -a UPLOAD_NAMES=()
declare -a RUST_VERSIONS=()

add_rust_version() {
    local version="$1"
    local existing
    for existing in "${RUST_VERSIONS[@]-}"; do
        [[ "$existing" == "$version" ]] && return
    done
    RUST_VERSIONS+=("$version")
}

add_asset() {
    local path="$1"
    local name="$2"
    [[ -s "$path" ]] || fail "预构建包不存在或为空: $path"
    UPLOAD_PATHS+=("$path")
    UPLOAD_NAMES+=("$name")
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
            INCLUDE_KDIR_MIN=true
            ;;
        --rust)
            INCLUDE_TARGET_RUST=true
            ;;
        --all-rust)
            INCLUDE_ALL_RUST=true
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
        --input)
            require_value "$1" "${2:-}"
            PREBUILTS_DIR="$2"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
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

[[ -n "$TARGET" ]] || fail "--target is required"
[[ -n "$HOST_PLATFORM" ]] || fail "--host-platform is required"
[[ -f "$MAP_FILE" ]] || fail "mapping.json not found: $MAP_FILE"
validate_host_platform
target_supports_platform || fail "$TARGET is not supported on $HOST_PLATFORM"

add_asset "$PREBUILTS_DIR/src/src.${TARGET}.tar.zst" \
    "src.${TARGET}.tar.zst"
add_asset "$PREBUILTS_DIR/kdir/${HOST_PLATFORM}/kdir.${TARGET}.tar.zst" \
    "kdir.${HOST_PLATFORM}.${TARGET}.tar.zst"

if [[ "$INCLUDE_KDIR_MIN" == true ]]; then
    add_asset "$PREBUILTS_DIR/kdir-min/${HOST_PLATFORM}/kdir.${TARGET}.tar.zst" \
        "kdir-min.${HOST_PLATFORM}.${TARGET}.tar.zst"
fi

if [[ "$INCLUDE_TARGET_RUST" == true ]]; then
    while IFS= read -r version; do
        [[ -n "$version" ]] && add_rust_version "$version"
    done < <(jq -r --arg target "$TARGET" --arg platform "$HOST_PLATFORM" '
        [.matrix[]
         | select(.android == $target and ((.platforms // []) | index($platform)))
         | .rust // empty]
        | unique[]
    ' "$MAP_FILE")
fi

if [[ "$INCLUDE_ALL_RUST" == true ]]; then
    while IFS= read -r version; do
        [[ -n "$version" ]] && add_rust_version "$version"
    done < <(jq -r --arg platform "$HOST_PLATFORM" '
        [.matrix[]
         | select((.platforms // []) | index($platform))
         | .rust // empty]
        | unique[]
    ' "$MAP_FILE")
fi

for version in "${RUST_VERSIONS[@]-}"; do
    [[ -n "$version" ]] || continue
    add_asset "$PREBUILTS_DIR/rust/${version}.tar.zst" "rust.${version}.tar.zst"
done

echo "[+] Release: $REPOSITORY@$RELEASE_TAG"
for index in "${!UPLOAD_PATHS[@]}"; do
    echo "[+] ${UPLOAD_PATHS[$index]} -> ${UPLOAD_NAMES[$index]}"
done

if [[ "$DRY_RUN" == true ]]; then
    exit 0
fi

command -v gh >/dev/null || fail "gh CLI is required to publish release assets"

if ! gh release view "$RELEASE_TAG" --repo "$REPOSITORY" >/dev/null 2>&1; then
    gh release create "$RELEASE_TAG" --repo "$REPOSITORY" \
        --title "Droid DDK prebuilts" \
        --notes "Droid DDK build input archives. Managed by build/publish-prebuilts.sh."
fi

UPLOAD_DIR="$(mktemp -d "$PREBUILTS_DIR/.release-upload.XXXXXX")"
cleanup() {
    rm -rf "$UPLOAD_DIR"
}
trap cleanup EXIT

for index in "${!UPLOAD_PATHS[@]}"; do
    upload_path="$UPLOAD_DIR/${UPLOAD_NAMES[$index]}"
    ln "${UPLOAD_PATHS[$index]}" "$upload_path"
    gh release upload "$RELEASE_TAG" \
        "$upload_path" \
        --repo "$REPOSITORY" --clobber
done

echo "[+] GitHub Release 资产已发布"
