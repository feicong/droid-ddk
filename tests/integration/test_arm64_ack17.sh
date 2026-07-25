#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
set -euo pipefail

KDIR="${1:?传入ARM64 kdir路径}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODULE_DIR="$ROOT/tests/fixtures/hello-module"

test -f "$KDIR/Module.symvers"
test -x "$KDIR/scripts/mod/modpost"
file "$KDIR/scripts/mod/modpost" | grep -Eq 'ARM aarch64|aarch64'
make -C "$MODULE_DIR" KDIR="$KDIR"
readelf -h "$MODULE_DIR/hello.ko" | grep -F 'AArch64'
modinfo "$MODULE_DIR/hello.ko" | grep -F 'license:        GPL'
make -C "$MODULE_DIR" KDIR="$KDIR" clean
