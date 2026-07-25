# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_droid_ddk", ROOT / "build" / "build-droid-ddk.py"
)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class BuildDroidDdkTest(unittest.TestCase):
    def setUp(self):
        self.mapping = json.loads((ROOT / "mapping.json").read_text())
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_root = BUILD.DROID_DDK_ROOT
        BUILD.DROID_DDK_ROOT = Path(self.temp_dir.name)

    def tearDown(self):
        BUILD.DROID_DDK_ROOT = self.original_root
        self.temp_dir.cleanup()

    def test_host_platform_normalizes_arm64_aliases(self):
        self.assertEqual(BUILD.host_platform("aarch64"), "linux-arm64")
        self.assertEqual(BUILD.host_platform("arm64"), "linux-arm64")

    def test_host_platform_rejects_unknown_machine(self):
        with self.assertRaises(ValueError):
            BUILD.host_platform("riscv64")

    def test_arm64_ndk_binary_path_uses_pinned_layout(self):
        expected = (
            BUILD.DROID_DDK_ROOT
            / "ndk"
            / "r29"
            / "toolchains/llvm/prebuilt/linux-x86_64/bin"
        )
        self.assertEqual(
            BUILD.toolchain_bin(
                self.mapping, "linux-arm64", "clang-r584948c", "r29"
            ),
            expected,
        )

    def test_arm64_matrix_contains_android17_only(self):
        targets = {
            item["android"]
            for item in BUILD.matrix_for_platform(self.mapping, "linux-arm64")
        }
        self.assertEqual(targets, {"android17-6.18"})

    def test_kdir_path_contains_host_platform(self):
        self.assertEqual(
            BUILD.kdir_path(BUILD.DROID_DDK_ROOT, "linux-arm64", "android17-6.18"),
            BUILD.DROID_DDK_ROOT / "kdir/linux-arm64/android17-6.18",
        )

    def test_arm64_rust_spec_selects_android17_toolchain(self):
        rust = BUILD.arm64_rust_spec(
            self.mapping, "linux-arm64", "rust-1.91.1"
        )
        self.assertEqual(rust["version"], "1.91.1")
        self.assertEqual(rust["bindgenVersion"], "0.72.1")

    def test_kernel_make_command_passes_rust_tools_as_make_variables(self):
        command = BUILD.kernel_make_command(
            {
                "RUSTC": "/toolchain/rustc",
                "RUSTFMT": "/toolchain/rustfmt",
                "BINDGEN": "/toolchain/bindgen",
                "RUST_LIB_SRC": "/toolchain/rust library",
                "HOSTCFLAGS": "-I/usr/include/libdwarf",
            },
            "O=/output modules_prepare",
        )
        self.assertIn("RUSTC=/toolchain/rustc", command)
        self.assertIn("RUSTFMT=/toolchain/rustfmt", command)
        self.assertIn("BINDGEN=/toolchain/bindgen", command)
        self.assertIn("RUST_LIB_SRC='/toolchain/rust library'", command)
        self.assertIn("HOSTCFLAGS=-I/usr/include/libdwarf", command)

    def test_arm64_bindgen_wrapper_unsets_directory_clang_path(self):
        cargo_bin = BUILD.DROID_DDK_ROOT / ".cargo/bin"
        cargo_bin.mkdir(parents=True)
        (cargo_bin / "bindgen").write_text("#!/bin/sh\n")
        wrapper = BUILD.ensure_arm64_bindgen_wrapper()
        self.assertTrue(wrapper.stat().st_mode & 0o111)
        self.assertIn("unset CLANG_PATH", wrapper.read_text())


if __name__ == "__main__":
    unittest.main()
