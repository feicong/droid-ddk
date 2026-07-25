#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/lib/platform.sh"

assert_eq() {
	[[ "$1" == "$2" ]] || {
		printf 'expected %s, got %s\n' "$2" "$1" >&2
		exit 1
	}
}

assert_eq "$(droid_ddk_normalize_machine x86_64)" "linux-amd64"
assert_eq "$(droid_ddk_normalize_machine amd64)" "linux-amd64"
assert_eq "$(droid_ddk_normalize_machine aarch64)" "linux-arm64"
assert_eq "$(droid_ddk_normalize_machine arm64)" "linux-arm64"
assert_eq "$(droid_ddk_normalize_platform linux/amd64)" "linux-amd64"
assert_eq "$(droid_ddk_normalize_platform linux-arm64)" "linux-arm64"
assert_eq "$(droid_ddk_docker_platform linux-arm64)" "linux/arm64"
assert_eq "$(droid_ddk_artifact_platform linux-amd64)" "linux-amd64"
