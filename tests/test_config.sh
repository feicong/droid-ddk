#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/dddk"

TEST_DIR="$ROOT/build/test-config-runtime-$$"
trap 'rm -rf "$TEST_DIR"' EXIT
mkdir -p "$TEST_DIR/home" "$TEST_DIR/project"

fail() {
	printf '%s\n' "$1" >&2
	exit 1
}

assert_eq() {
	[[ "$1" == "$2" ]] || fail "expected '$2', got '$1'"
}

HOME="$TEST_DIR/home"
DROID_DDK_PROJECT_CONFIG="$TEST_DIR/project/.dddk-config"

cat > "$DROID_DDK_PROJECT_CONFIG" <<'EOF'
# Project-local Droid DDK configuration.
mode=docker
source=github
EOF

DROID_DDK_MODE=""
SOURCE=""
load_project_config
assert_eq "$DROID_DDK_MODE" docker
assert_eq "$SOURCE" github

printf 'mode=docker\nunknown=value\nsource=github\n' > "$DROID_DDK_PROJECT_CONFIG"
if (load_project_config >/dev/null 2>&1); then
	fail 'unknown configuration key was accepted'
fi

printf 'mode=docker\n' > "$DROID_DDK_PROJECT_CONFIG"
if (load_project_config >/dev/null 2>&1); then
	fail 'incomplete configuration was accepted'
fi

DROID_DDK_MODE=docker
SOURCE=docker
write_project_config
assert_eq "$(cat "$DROID_DDK_PROJECT_CONFIG")" $'mode=docker\nsource=docker'
[[ ! -e "$HOME/.droid-ddk/source" ]] || fail 'legacy source file was created'
[[ ! -e "$HOME/.droid-ddk/mode" ]] || fail 'legacy mode file was created'
