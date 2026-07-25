#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAPPING_FILE="${MAPPING_FILE:-$SCRIPT_DIR/../mapping.json}"
REGISTRY_TYPE="${REGISTRY_TYPE:-docker}"
DATE_TAG="${DATE_TAG:-$(date +%Y%m%d)}"
PROJECTS=(droid-ddk droid-ddk-min droid-ddk-toolchain)

command -v jq >/dev/null 2>&1 || {
    printf 'Error: jq is required\n' >&2
    exit 1
}
command -v docker >/dev/null 2>&1 || {
    printf 'Error: docker is required\n' >&2
    exit 1
}
[[ -f "$MAPPING_FILE" ]] || {
    printf 'Error: mapping file not found: %s\n' "$MAPPING_FILE" >&2
    exit 1
}

for project in "${PROJECTS[@]}"; do
    image=$(jq -er \
        --arg project "$project" \
        --arg registry "$REGISTRY_TYPE" \
        '.registry[$project][$registry]' \
        "$MAPPING_FILE")
    found=false

    while IFS= read -r source; do
        [[ -n "$source" ]] || continue
        found=true
        tag="${source##*:}"
        destination="${image}:${tag}-${DATE_TAG}"
        printf '%s -> %s\n' "$source" "$destination"
        docker tag "$source" "$destination"
        docker push "$source"
        docker push "$destination"
    done < <(docker image ls "$image" --format '{{.Repository}}:{{.Tag}}' | awk '$0 !~ /:<none>$/')

    if [[ "$found" == false ]]; then
        printf 'No local tags found for %s\n' "$image"
    fi
done
