# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DockerfileContractTest(unittest.TestCase):
    def test_builder_uses_ubuntu_26_and_native_libxml2_compat(self):
        dockerfile = (ROOT / "docker/ddk-builder/Dockerfile").read_text()
        self.assertIn("FROM ubuntu:26.04", dockerfile)
        self.assertIn("libxml2-2.9.14.tar.xz", dockerfile)
        self.assertIn(
            "60d74a257d1ccec0475e749cba2f21559e48139efba6ff28224357c7c798dfee",
            dockerfile,
        )
        self.assertIn("LD_LIBRARY_PATH=/opt/droid-ddk/compat/lib", dockerfile)

    def test_toolchain_supports_zip_and_tar_ndk_archives(self):
        dockerfile = (ROOT / "docker/ddk-toolchain/Dockerfile").read_text()
        self.assertIn("ARG NDK_ARCHIVE_TYPE", dockerfile)
        self.assertIn("zip) unzip", dockerfile)
        self.assertIn("tar.gz) tar -xzf", dockerfile)

    def test_toolchain_accepts_target_host_cflags(self):
        dockerfile = (ROOT / "docker/ddk-toolchain/Dockerfile").read_text()
        makefile = (ROOT / "docker/Makefile").read_text()
        self.assertIn("ARG KERNEL_HOSTCFLAGS", dockerfile)
        self.assertIn(
            'HOSTCFLAGS="-I/usr/include/libdwarf ${KERNEL_HOSTCFLAGS}"',
            dockerfile,
        )
        self.assertIn(
            '--build-arg KERNEL_HOSTCFLAGS="$$KERNEL_HOSTCFLAGS"',
            makefile,
        )

    def test_kernel_images_restore_recorded_build_paths(self):
        for name in ("ddk", "ddk-min"):
            dockerfile = (ROOT / f"docker/{name}/Dockerfile").read_text()
            self.assertIn(
                'kernel_src="/opt/droid-ddk/src/${ANDROID_VER}"',
                dockerfile,
            )
            self.assertIn(
                'kernel_out="/opt/droid-ddk/kdir/${artifact_platform}/${ANDROID_VER}"',
                dockerfile,
            )
            self.assertIn(
                'recorded_src="$(sed -n',
                dockerfile,
            )
            self.assertIn(
                'ln -s "$kernel_src" "$recorded_src"',
                dockerfile,
            )

    def test_makefile_selects_ndk_platform_from_host_architecture(self):
        makefile = (ROOT / "docker/Makefile").read_text()
        self.assertIn("DETECTED_MACHINE := $(shell uname -m)", makefile)
        self.assertIn(
            "$(filter arm64 aarch64,$(DETECTED_MACHINE)),linux-arm64,linux-amd64",
            makefile,
        )
        self.assertIn(
            "PLAT ?= $(if $(filter linux-arm64,$(HOST_PLATFORM)),linux/arm64,linux/amd64)",
            makefile,
        )

    def test_makefile_can_filter_toolchain_matrix_by_version(self):
        makefile = (ROOT / "docker/Makefile").read_text()
        self.assertIn('--arg version "$(VER)"', makefile)
        self.assertIn('$$version == "" or .android == $$version', makefile)

if __name__ == "__main__":
    unittest.main()
