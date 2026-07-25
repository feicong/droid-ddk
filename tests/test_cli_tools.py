# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "android14-5.15",
    "android14-6.1",
    "android15-6.6",
    "android16-6.12",
    "android17-6.18",
]


def run(*args, env=None):
    return subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


class CliToolsTest(unittest.TestCase):
    def test_image_sync_uses_renamed_projects_and_enabled_targets(self):
        result = run(
            ROOT / "build/sync-image.sh",
            "-s",
            "github",
            "-d",
            "docker",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 15)
        self.assertTrue(all("droid-ddk" in line for line in lines))
        self.assertTrue(all("docker.io/fsx199" in line for line in lines))
        for target in TARGETS:
            self.assertEqual(sum(target in line for line in lines), 3)
        self.assertNotIn("android12", result.stdout)
        self.assertNotIn("android13", result.stdout)

    def test_image_sync_rejects_disabled_target(self):
        result = run(
            ROOT / "build/sync-image.sh",
            "-s",
            "github",
            "-d",
            "docker",
            "-t",
            "android13-5.15",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("unsupported target", result.stdout)

    def test_make_toolchain_version_filter_is_platform_specific(self):
        arm64 = run(
            "make",
            "-C",
            "docker",
            "list",
            "VER=android17-6.18",
            "PLAT=linux/arm64",
        )
        amd64 = run(
            "make",
            "-C",
            "docker",
            "list",
            "VER=android15-6.6",
            "PLAT=linux/amd64",
        )
        self.assertEqual(arm64.returncode, 0, arm64.stdout)
        self.assertEqual(amd64.returncode, 0, amd64.stdout)
        self.assertEqual(
            arm64.stdout.strip(),
            "android17-6.18:clang-r584948c:rust-1.91.1:r29",
        )
        self.assertEqual(
            amd64.stdout.strip(),
            "android15-6.6:clang-r510928::r25c",
        )

    def test_make_toolchains_rejects_disabled_version(self):
        result = run(
            "make",
            "-C",
            "docker",
            "toolchains",
            "VER=android13-5.15",
            "PLAT=linux/arm64",
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("VER=android13-5.15", result.stdout)

    def test_dddk_lists_only_enabled_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".droid-ddk"
            config.mkdir()
            (config / "source").write_text("github\n")
            (config / "mode").write_text("docker\n")
            (config / "mapping.json").write_text(
                (ROOT / "mapping.json").read_text()
            )
            env = os.environ.copy()
            env["HOME"] = str(home)
            result = run(ROOT / "scripts/dddk", "list-all", env=env)

        self.assertEqual(result.returncode, 0, result.stdout)
        listed = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip().startswith("android")
        ]
        self.assertEqual(listed, TARGETS)

    def test_dddk_passes_selected_host_platform_to_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            config = home / ".droid-ddk"
            fake_bin = base / "bin"
            log = base / "docker-args"
            config.mkdir(parents=True)
            fake_bin.mkdir()
            (config / "source").write_text("github\n")
            (config / "mode").write_text("docker\n")
            docker = fake_bin / "docker"
            docker.write_text(
                "#!/bin/sh\n"
                "# Copyright (c) 2025-2026 "
                "fei_cong(https://github.com/feicong/feicong-course)\n"
                "printf '%s\\n' \"$@\" > \"$DROID_DDK_TEST_LOG\"\n"
            )
            docker.chmod(0o755)

            env = os.environ.copy()
            env.update(
                HOME=str(home),
                PATH=f"{fake_bin}:{env['PATH']}",
                DROID_DDK_TEST_LOG=str(log),
            )
            result = run(
                ROOT / "scripts/dddk",
                "build",
                "android17-6.18",
                "--platform",
                "linux/arm64",
                env=env,
            )
            arguments = log.read_text().splitlines()

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(arguments[0:3], ["run", "--platform", "linux/arm64"])
        self.assertIn("ghcr.io/feicong/droid-ddk:android17-6.18", arguments)

    def test_clangd_path_uses_host_specific_ndk_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            config = home / ".droid-ddk"
            root = base / "root"
            (root / "src/android17-6.18").mkdir(parents=True)
            config.mkdir(parents=True)
            (config / "mapping.json").write_text(
                (ROOT / "mapping.json").read_text()
            )

            env = os.environ.copy()
            env.update(
                HOME=str(home),
                DROID_DDK_ROOT=str(root),
                DROID_DDK_PLATFORM="linux-arm64",
            )
            arm64 = run(
                ROOT / "host/vscode_clangd_configure.sh",
                "--dry-run",
                env=env,
            )
            env["DROID_DDK_PLATFORM"] = "linux-amd64"
            amd64 = run(
                ROOT / "host/vscode_clangd_configure.sh",
                "--dry-run",
                env=env,
            )

        self.assertEqual(arm64.returncode, 0, arm64.stdout)
        self.assertEqual(amd64.returncode, 0, amd64.stdout)
        self.assertIn("/ndk/r29/", arm64.stdout)
        self.assertIn("/ndk/android-ndk-r29/", amd64.stdout)


if __name__ == "__main__":
    unittest.main()
