#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VSCODE_TEMPLATE_DIR="$SCRIPT_DIR/.vscode"
DROID_DDK_CONFIG_DIR="$HOME/.droid-ddk"
DROID_DDK_MAPPING_JSON="$DROID_DDK_CONFIG_DIR/mapping.json"
DDK_ROOT="${DDK_ROOT:-/opt/droid-ddk}"
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run]

Environment:
  DDK_ROOT       Installation path, default: /opt/droid-ddk
  DROID_DDK_PLATFORM   linux-amd64 or linux-arm64
EOF
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 2
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

host_platform() {
    if [[ -n "${DROID_DDK_PLATFORM:-}" ]]; then
        case "$DROID_DDK_PLATFORM" in
            linux-amd64|linux-arm64)
                printf '%s\n' "$DROID_DDK_PLATFORM"
                return
                ;;
            linux/amd64)
                printf '%s\n' linux-amd64
                return
                ;;
            linux/arm64)
                printf '%s\n' linux-arm64
                return
                ;;
            *) fail "unsupported platform: $DROID_DDK_PLATFORM" ;;
        esac
    fi

    case "$(uname -m)" in
        x86_64|amd64) printf '%s\n' linux-amd64 ;;
        aarch64|arm64) printf '%s\n' linux-arm64 ;;
        *) fail "unsupported Linux host architecture: $(uname -m)" ;;
    esac
}

toolchain_bin() {
    local platform="$1"
    local index="$2"
    local kind
    kind=$(jq -r --arg platform "$platform" '.platforms[$platform].toolchainKind' "$DROID_DDK_MAPPING_JSON")

    if [[ "$kind" == android-ndk ]]; then
        local ndk
        local root
        local bin
        ndk=$(jq -r ".matrix[$index].ndk" "$DROID_DDK_MAPPING_JSON")
        root=$(jq -r --arg platform "$platform" --arg ndk "$ndk" '.platforms[$platform].ndks[$ndk].root' "$DROID_DDK_MAPPING_JSON")
        bin=$(jq -r --arg platform "$platform" --arg ndk "$ndk" '.platforms[$platform].ndks[$ndk].bin' "$DROID_DDK_MAPPING_JSON")
        printf '%s\n' "$DDK_ROOT/ndk/$root/$bin"
        return
    fi

    local clang
    clang=$(jq -r ".matrix[$index].clang" "$DROID_DDK_MAPPING_JSON")
    printf '%s\n' "$DDK_ROOT/clang/$clang/bin"
}

update_settings() {
    local settings_file="$1"
    local clangd_path="$2"
    local temporary

    mkdir -p "$(dirname "$settings_file")"
    if [[ -f "$settings_file" ]]; then
        temporary=$(mktemp)
        jq --arg path "$clangd_path" '. + {"clangd.path": $path}' "$settings_file" > "$temporary"
        mv "$temporary" "$settings_file"
    else
        jq -n --arg path "$clangd_path" '{"clangd.path": $path}' > "$settings_file"
    fi
}

configure_target() {
    local platform="$1"
    local index="$2"
    local android
    local source_dir
    local clangd_path
    local vscode_dir

    android=$(jq -r ".matrix[$index].android" "$DROID_DDK_MAPPING_JSON")
    source_dir="$DDK_ROOT/src/$android"
    clangd_path="$(toolchain_bin "$platform" "$index")/clangd"
    vscode_dir="$source_dir/.vscode"

    [[ -d "$source_dir" ]] || return 0
    if [[ "$DRY_RUN" == true ]]; then
        printf '%s -> %s\n' "$android" "$clangd_path"
        return
    fi

    mkdir -p "$vscode_dir"
    if [[ -d "$VSCODE_TEMPLATE_DIR" ]]; then
        cp -R "$VSCODE_TEMPLATE_DIR/." "$vscode_dir/"
    fi
    update_settings "$vscode_dir/settings.json" "$clangd_path"
    printf '[+] %s -> %s\n' "$android" "$clangd_path"
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run) DRY_RUN=true ;;
            -h|--help) usage; exit 0 ;;
            *) fail "unknown option: $1" ;;
        esac
        shift
    done

    require_command jq
    [[ -f "$DROID_DDK_MAPPING_JSON" ]] || fail "run 'dddk update' to create $DROID_DDK_MAPPING_JSON"
    [[ -d "$DDK_ROOT" ]] || fail "Droid DDK root not found: $DDK_ROOT"

    local platform
    local count
    local index
    platform=$(host_platform)
    count=$(jq '.matrix | length' "$DROID_DDK_MAPPING_JSON")
    for ((index = 0; index < count; index++)); do
        if jq -e --arg platform "$platform" ".matrix[$index].platforms | index(\$platform)" "$DROID_DDK_MAPPING_JSON" >/dev/null; then
            configure_target "$platform" "$index"
        fi
    done
}

main "$@"
