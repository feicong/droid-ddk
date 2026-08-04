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
version=android15-6.6
mode=docker
source=github
EOF

DROID_DDK_VERSION=""
DROID_DDK_MODE=""
DROID_DDK_SLIM=false
SOURCE=""
load_project_config
assert_eq "$DROID_DDK_VERSION" android15-6.6
assert_eq "$DROID_DDK_MODE" docker
assert_eq "$SOURCE" github
assert_eq "$DROID_DDK_SLIM" false

printf 'version=android16-6.12\nmode=docker\nsource=github\nslim=true\n' > "$DROID_DDK_PROJECT_CONFIG"
load_project_config
assert_eq "$DROID_DDK_SLIM" true

printf 'version=android15-6.6\nmode=docker\nunknown=value\nsource=github\n' > "$DROID_DDK_PROJECT_CONFIG"
if (load_project_config >/dev/null 2>&1); then
	fail 'unknown configuration key was accepted'
fi

printf 'version=android15-6.6\nmode=docker\nsource=github\nslim=true\nslim=false\n' > "$DROID_DDK_PROJECT_CONFIG"
if (load_project_config >/dev/null 2>&1); then
	fail 'duplicate slim configuration was accepted'
fi

printf 'version=android15-6.6\nmode=docker\nsource=github\nslim=invalid\n' > "$DROID_DDK_PROJECT_CONFIG"
if (load_project_config >/dev/null 2>&1); then
	fail 'invalid slim configuration was accepted'
fi

printf 'mode=docker\nsource=github\n' > "$DROID_DDK_PROJECT_CONFIG"
if (load_project_config >/dev/null 2>&1); then
	fail 'incomplete configuration was accepted'
fi

DROID_DDK_VERSION=android16-6.12
DROID_DDK_MODE=docker
DROID_DDK_SLIM=true
SOURCE=github
write_project_config
assert_eq "$(cat "$DROID_DDK_PROJECT_CONFIG")" $'version=android16-6.12\nmode=docker\nsource=github\nslim=true'
[[ ! -e "$HOME/.droid-ddk/source" ]] || fail 'legacy source file was created'
[[ ! -e "$HOME/.droid-ddk/mode" ]] || fail 'legacy mode file was created'

mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/docker" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$DDDK_DOCKER_LOG"
EOF
chmod 0755 "$TEST_DIR/bin/docker"
(
	cd "$TEST_DIR/project"
	DDDK_DOCKER_LOG="$TEST_DIR/docker.log" \
		PATH="$TEST_DIR/bin:$PATH" \
		HOME="$HOME" \
		"$ROOT/scripts/dddk" build > "$TEST_DIR/build.stdout"
)
grep -Fq 'Using target from .dddk-config: android16-6.12' "$TEST_DIR/build.stdout" || \
	fail 'project config version was not selected as the default target'
grep -Fq 'ghcr.io/feicong/droid-ddk-min:android16-6.12' "$TEST_DIR/docker.log" || \
	fail 'slim project config was not used for the build image'
