# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAPPING = json.loads((ROOT / "mapping.json").read_text())


class MappingContractTest(unittest.TestCase):
    def test_android17_ack_target_uses_official_lts_branch(self):
        target = next(item for item in MAPPING["android"] if item["name"] == "android17-6.18")
        self.assertEqual(target["branch"], "android17-6.18-lts")
        self.assertEqual(target["arch"], "arm64")
        self.assertEqual(target["pageSize"], "4k")

    def test_android17_uses_its_declared_toolchain_versions(self):
        matrix = next(item for item in MAPPING["matrix"] if item["android"] == "android17-6.18")
        self.assertEqual(matrix["clang"], "clang-r584948c")
        self.assertEqual(matrix["rust"], "rust-1.91.1")
        self.assertEqual(matrix["ndk"], "r29")
        self.assertEqual(matrix["platforms"], ["linux-amd64", "linux-arm64"])

    def test_linux_arm64_ndk_is_pinned(self):
        ndks = MAPPING["platforms"]["linux-arm64"]["ndks"]
        r29 = ndks["r29"]
        self.assertEqual(r29["release"], "0.0.2")
        self.assertEqual(r29["archive"], "android-ndk-r29-linux-aarch64.tar.gz")
        self.assertEqual(r29["archiveType"], "tar.gz")
        self.assertEqual(r29["sha256"], "48cb104c28e1ede5e1884b0b34d97d28c4df74cd4e8f7628202a4c2c8de78a50")
        self.assertEqual(r29["root"], "r29")
        self.assertEqual(r29["bin"], "toolchains/llvm/prebuilt/linux-x86_64/bin")

        r25c = ndks["r25c"]
        self.assertEqual(r25c["release"], "0.0.1")
        self.assertEqual(r25c["archive"], "android-ndk-r25c-aarch64-linux.tgz")
        self.assertEqual(r25c["archiveType"], "tar.gz")
        self.assertEqual(r25c["sha256"], "cfe49e478cd635e209a3cff2639bdcfb23c6c932ef73d08bdf8ac6cc75f2bc5d")
        self.assertEqual(r25c["root"], "25.2.9519653")

    def test_linux_amd64_uses_official_r29_ndk(self):
        platform = MAPPING["platforms"]["linux-amd64"]
        r29 = platform["ndks"]["r29"]
        self.assertEqual(platform["toolchainKind"], "android-ndk")
        self.assertEqual(r29["release"], "29.0.14206865")
        self.assertEqual(r29["archiveType"], "zip")
        self.assertEqual(r29["root"], "android-ndk-r29")
        self.assertEqual(r29["sha256"], "4abbbcdc842f3d4879206e9695d52709603e52dd68d3c1fff04b3b5e7a308ecf")

        r25c = platform["ndks"]["r25c"]
        self.assertEqual(r25c["release"], "25.2.9519653")
        self.assertEqual(r25c["archiveType"], "zip")
        self.assertEqual(r25c["root"], "android-ndk-r25c")
        self.assertEqual(r25c["sha256"], "769ee342ea75f80619d985c2da990c48b3d8eaf45f48783a2d48870d04b46108")

    def test_linux_arm64_rust_toolchains_include_android16_and_android17(self):
        rust = MAPPING["platforms"]["linux-arm64"]["rust"]
        self.assertEqual(rust["toolchains"]["rust-1.82.0"]["version"], "1.82.0")
        self.assertEqual(rust["toolchains"]["rust-1.91.1"]["version"], "1.91.1")
        self.assertEqual(MAPPING["platforms"]["linux-arm64"]["libclangPath"], "/usr/lib/llvm-22/lib")

    def test_supported_targets_select_explicit_ndk_and_platforms(self):
        matrix = {item["android"]: item for item in MAPPING["matrix"]}
        self.assertEqual(matrix["android13-5.15"]["ndk"], "r25c")
        self.assertEqual(matrix["android14-5.15"]["ndk"], "r25c")
        self.assertEqual(matrix["android14-6.1"]["ndk"], "r25c")
        self.assertEqual(matrix["android15-6.6"]["ndk"], "r25c")
        self.assertEqual(
            matrix["android15-6.6"]["hostCFlags"],
            "-DUSE_PKCS11_ENGINE",
        )
        self.assertEqual(matrix["android16-6.12"]["ndk"], "r29")
        self.assertEqual(matrix["android17-6.18"]["ndk"], "r29")
        for target in (
            "android13-5.15",
            "android14-5.15",
            "android14-6.1",
            "android15-6.6",
            "android16-6.12",
            "android17-6.18",
        ):
            self.assertEqual(
                matrix[target]["platforms"],
                ["linux-amd64", "linux-arm64"],
            )

        for target in ("android12-5.10", "android13-5.10"):
            self.assertEqual(matrix[target]["platforms"], [])

    def test_android13_and_android14_use_thin_lto(self):
        matrix = {item["android"]: item for item in MAPPING["matrix"]}
        self.assertEqual(matrix["android13-5.15"]["lto"], "thin")
        self.assertEqual(matrix["android14-5.15"]["lto"], "thin")
        self.assertEqual(matrix["android14-6.1"]["lto"], "thin")
        self.assertEqual(
            matrix["android14-6.1"]["hostCFlags"],
            "-Wno-error=incompatible-pointer-types-discards-qualifiers "
            "-DUSE_PKCS11_ENGINE",
        )


if __name__ == "__main__":
    unittest.main()
