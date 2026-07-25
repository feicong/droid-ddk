# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


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

    def test_amd64_ndk_binary_path_uses_official_layout(self):
        expected = (
            BUILD.DROID_DDK_ROOT
            / "ndk"
            / "android-ndk-r29"
            / "toolchains/llvm/prebuilt/linux-x86_64/bin"
        )
        self.assertEqual(
            BUILD.toolchain_bin(
                self.mapping, "linux-amd64", "clang-r584948c", "r29"
            ),
            expected,
        )

    def test_arm64_r25c_binary_path_uses_snownf_layout(self):
        expected = (
            BUILD.DROID_DDK_ROOT
            / "ndk"
            / "25.2.9519653"
            / "toolchains/llvm/prebuilt/linux-x86_64/bin"
        )
        self.assertEqual(
            BUILD.toolchain_bin(
                self.mapping, "linux-arm64", "clang-r510928", "r25c"
            ),
            expected,
        )

    def test_amd64_r25c_binary_path_uses_official_layout(self):
        expected = (
            BUILD.DROID_DDK_ROOT
            / "ndk"
            / "android-ndk-r25c"
            / "toolchains/llvm/prebuilt/linux-x86_64/bin"
        )
        self.assertEqual(
            BUILD.toolchain_bin(
                self.mapping, "linux-amd64", "clang-r510928", "r25c"
            ),
            expected,
        )

    def test_android15_adds_target_host_cflags(self):
        ndk_bin = (
            BUILD.DROID_DDK_ROOT
            / "ndk"
            / "25.2.9519653"
            / "toolchains/llvm/prebuilt/linux-x86_64/bin"
        )
        ndk_bin.mkdir(parents=True)
        target = next(
            item
            for item in self.mapping["matrix"]
            if item["android"] == "android15-6.6"
        )
        with patch.dict(os.environ, {"HOSTCFLAGS": ""}):
            env = BUILD._make_kernel_env(
                self.mapping,
                "linux-arm64",
                target["clang"],
                ndk_version=target["ndk"],
                kernel_host_cflags=target["hostCFlags"],
            )
        self.assertEqual(
            env["HOSTCFLAGS"],
            "-I/usr/include/libdwarf -DUSE_PKCS11_ENGINE",
        )

    def test_arm64_matrix_contains_android15_to_android17(self):
        targets = {
            item["android"]
            for item in BUILD.matrix_for_platform(self.mapping, "linux-arm64")
        }
        self.assertEqual(
            targets, {"android15-6.6", "android16-6.12", "android17-6.18"}
        )

    def test_amd64_matrix_contains_android15_to_android17(self):
        targets = {
            item["android"]
            for item in BUILD.matrix_for_platform(self.mapping, "linux-amd64")
        }
        self.assertEqual(
            targets, {"android15-6.6", "android16-6.12", "android17-6.18"}
        )

    def test_extract_archive_supports_official_ndk_zip(self):
        root = Path(self.temp_dir.name)
        archive = root / "ndk.zip"
        destination = root / "extract"
        destination.mkdir()
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("android-ndk-r29/toolchains/llvm/bin/clang", "")
        BUILD.extract_archive(archive, destination, "zip")
        self.assertTrue(
            (destination / "android-ndk-r29/toolchains/llvm/bin/clang").is_file()
        )

    def test_kdir_path_contains_host_platform(self):
        self.assertEqual(
            BUILD.kdir_path(BUILD.DROID_DDK_ROOT, "linux-arm64", "android17-6.18"),
            BUILD.DROID_DDK_ROOT / "kdir/linux-arm64/android17-6.18",
        )

    def test_arm64_rust_spec_selects_android16_toolchain(self):
        rust = BUILD.arm64_rust_spec(
            self.mapping, "linux-arm64", "rust-1.82.0"
        )
        self.assertEqual(rust["version"], "1.82.0")
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

    def test_android16_enables_cfi_integer_normalization_symbol(self):
        with patch.object(BUILD, "run") as run:
            BUILD._configure_kernel(
                Path("/kernel/src"),
                Path("/kernel/out"),
                {},
                android_branch="android16-6.12",
            )
        commands = "\n".join(call.args[0] for call in run.call_args_list)
        self.assertIn("-e CFI_ICALL_NORMALIZE_INTEGERS", commands)
        self.assertNotIn("-e CONFIG_CFI_ICALL_NORMALIZE_INTEGERS", commands)

    def test_arm64_bindgen_wrapper_unsets_directory_clang_path(self):
        cargo_bin = BUILD.DROID_DDK_ROOT / ".cargo/bin"
        cargo_bin.mkdir(parents=True)
        (cargo_bin / "bindgen").write_text("#!/bin/sh\n")
        wrapper = BUILD.ensure_arm64_bindgen_wrapper()
        self.assertTrue(wrapper.stat().st_mode & 0o111)
        self.assertIn("unset CLANG_PATH", wrapper.read_text())


if __name__ == "__main__":
    unittest.main()
