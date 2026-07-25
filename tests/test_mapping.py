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
        self.assertIn("linux-arm64", matrix["platforms"])

    def test_linux_arm64_ndk_r29_is_pinned(self):
        r29 = MAPPING["platforms"]["linux-arm64"]["ndks"]["r29"]
        self.assertEqual(r29["release"], "0.0.2")
        self.assertEqual(r29["archive"], "android-ndk-r29-linux-aarch64.tar.gz")
        self.assertEqual(r29["sha256"], "48cb104c28e1ede5e1884b0b34d97d28c4df74cd4e8f7628202a4c2c8de78a50")
        self.assertEqual(r29["root"], "r29")
        self.assertEqual(r29["archiveType"], "tar.gz")
        self.assertEqual(r29["bin"], "toolchains/llvm/prebuilt/linux-x86_64/bin")

    def test_linux_amd64_uses_official_r29_ndk(self):
        platform = MAPPING["platforms"]["linux-amd64"]
        r29 = platform["ndks"]["r29"]
        self.assertEqual(platform["toolchainKind"], "android-ndk")
        self.assertEqual(r29["release"], "29.0.14206865")
        self.assertEqual(r29["archiveType"], "zip")
        self.assertEqual(r29["root"], "android-ndk-r29")
        self.assertEqual(r29["sha256"], "4abbbcdc842f3d4879206e9695d52709603e52dd68d3c1fff04b3b5e7a308ecf")

    def test_android16_and_android17_use_r29(self):
        matrix = {item["android"]: item for item in MAPPING["matrix"]}
        for target in ("android16-6.12", "android17-6.18"):
            self.assertEqual(matrix[target]["ndk"], "r29")
            self.assertEqual(
                matrix[target]["platforms"], ["linux-amd64", "linux-arm64"]
            )
        rust = MAPPING["platforms"]["linux-arm64"]["rust"]["toolchains"]
        self.assertEqual(rust["rust-1.82.0"]["version"], "1.82.0")
        self.assertEqual(rust["rust-1.91.1"]["version"], "1.91.1")


if __name__ == "__main__":
    unittest.main()
