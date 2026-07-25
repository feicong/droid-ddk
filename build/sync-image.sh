#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAPPING_FILE="${MAPPING_FILE:-$SCRIPT_DIR/../mapping.json}"
SRC_REGISTRY_TYPE=""
DST_REGISTRY_TYPE=""
PROJECT="all"
TAG_FILTER=""
USE_DATE=""
NEW_DATE=""
DRY_RUN=false
PROJECTS=(droid-ddk droid-ddk-min droid-ddk-toolchain)

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Sync Droid DDK container images between registries.

Options:
  -s, --src <registry>     Source registry (github|docker|cnb)
  -d, --dst <registry>     Destination registry (github|docker|cnb)
  -p, --project <name>     droid-ddk|droid-ddk-min|droid-ddk-toolchain|all
  -t, --tag <tag>          Sync one supported Android target
  -m, --mapping <file>     Path to mapping.json
  --date <date>            Read and write the existing dated tag
  --new-date <date>        Read the base tag and write a dated tag
  --dry-run                Print operations without copying images
  -h, --help               Show this help
EOF
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 2
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

registry_image() {
    local project="$1"
    local registry_type="$2"
    jq -er \
        --arg project "$project" \
        --arg registry "$registry_type" \
        '.registry[$project][$registry] | select(type == "string" and length > 0)' \
        "$MAPPING_FILE"
}

supported_tags() {
    jq -r \
        '[.matrix[] | select((.platforms // []) | length > 0) | .android] | unique[]' \
        "$MAPPING_FILE"
}

is_supported_tag() {
    local tag="$1"
    jq -e \
        --arg tag "$tag" \
        'any(.matrix[]; .android == $tag and ((.platforms // []) | length > 0))' \
        "$MAPPING_FILE" >/dev/null
}

sync_image() {
    local src_image="$1"
    local dst_image="$2"
    local base_tag="$3"
    local src_tag="$base_tag"
    local dst_tag="$base_tag"

    if [[ -n "$USE_DATE" ]]; then
        src_tag="${base_tag}-${USE_DATE}"
        dst_tag="$src_tag"
    elif [[ -n "$NEW_DATE" ]]; then
        dst_tag="${base_tag}-${NEW_DATE}"
    fi

    local src_full="${src_image}:${src_tag}"
    local dst_full="${dst_image}:${dst_tag}"
    printf '%s\n' "${src_full} -> ${dst_full}"

    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    skopeo copy "docker://${src_full}" "docker://${dst_full}"
}

sync_project() {
    local project="$1"
    local src_image
    local dst_image
    src_image=$(registry_image "$project" "$SRC_REGISTRY_TYPE")
    dst_image=$(registry_image "$project" "$DST_REGISTRY_TYPE")

    if [[ -n "$TAG_FILTER" ]]; then
        sync_image "$src_image" "$dst_image" "$TAG_FILTER"
        return
    fi

    local tag
    while IFS= read -r tag; do
        [[ -n "$tag" ]] || continue
        sync_image "$src_image" "$dst_image" "$tag"
    done < <(supported_tags)
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--src)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            SRC_REGISTRY_TYPE="$2"
            shift 2
            ;;
        -d|--dst)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            DST_REGISTRY_TYPE="$2"
            shift 2
            ;;
        -p|--project)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            PROJECT="$2"
            shift 2
            ;;
        -t|--tag)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            TAG_FILTER="$2"
            shift 2
            ;;
        -m|--mapping)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            MAPPING_FILE="$2"
            shift 2
            ;;
        --date)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            USE_DATE="$2"
            shift 2
            ;;
        --new-date)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            NEW_DATE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
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
done

require_command jq
[[ -f "$MAPPING_FILE" ]] || fail "mapping file not found: $MAPPING_FILE"
[[ -n "$SRC_REGISTRY_TYPE" ]] || fail "source registry is required"
[[ -n "$DST_REGISTRY_TYPE" ]] || fail "destination registry is required"
[[ -z "$USE_DATE" || -z "$NEW_DATE" ]] || fail "--date and --new-date are mutually exclusive"

case "$PROJECT" in
    all|droid-ddk|droid-ddk-min|droid-ddk-toolchain) ;;
    *) fail "unknown project: $PROJECT" ;;
esac

if [[ -n "$TAG_FILTER" ]]; then
    is_supported_tag "$TAG_FILTER" || fail "unsupported target: $TAG_FILTER"
fi

if [[ "$DRY_RUN" != true ]]; then
    require_command skopeo
fi

if [[ "$PROJECT" == all ]]; then
    for project in "${PROJECTS[@]}"; do
        sync_project "$project"
    done
else
    sync_project "$PROJECT"
fi
