#!/usr/bin/env python3
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import threading
import urllib.request
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DROID_DDK_ROOT = Path(os.environ.get("DROID_DDK_ROOT", "/opt/droid-ddk"))
DEFAULT_MAP_FILE = PROJECT_ROOT / "mapping.json"
PREBUILTS_DIR = PROJECT_ROOT / "prebuilts"


def run(cmd, cwd=None, env=None):
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"[x] 命令失败 (exit {result.returncode}): {cmd}")
        sys.exit(result.returncode)


def capture(cmd, cwd=None, env=None):
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(f"[x] 命令失败 (exit {result.returncode}): {cmd}")
        sys.exit(result.returncode)
    return result.stdout.strip()


def load_mapping(map_file):
    if not map_file.is_file():
        print(f"[x] 未找到 mapping.json: {map_file}")
        sys.exit(2)
    with open(map_file) as f:
        return json.load(f)


def host_platform(machine=None):
    if machine is None:
        if sys.platform != "linux":
            raise ValueError(f"仅支持Linux宿主机：{sys.platform}")
        machine = os.uname().machine
    aliases = {
        "x86_64": "linux-amd64",
        "amd64": "linux-amd64",
        "aarch64": "linux-arm64",
        "arm64": "linux-arm64",
    }
    try:
        return aliases[machine.lower()]
    except KeyError as exc:
        raise ValueError(f"不支持的Linux宿主架构：{machine}") from exc


def platform_config(mapping, platform_name):
    try:
        return mapping["platforms"][platform_name]
    except KeyError as exc:
        raise ValueError(f"mapping.json缺少平台配置：{platform_name}") from exc


def matrix_for_platform(mapping, platform_name, android_ver=None):
    """返回指定宿主平台可构建的目标矩阵条目。"""
    entries = [
        item for item in mapping.get("matrix", [])
        if platform_name in item["platforms"]
    ]
    if android_ver:
        entries = [item for item in entries if item.get("android") == android_ver]
    return entries


def ndk_spec(mapping, platform_name, ndk_version):
    """读取目标宿主平台显式指定的NDK配置。"""
    platform = platform_config(mapping, platform_name)
    if platform.get("toolchainKind") != "android-ndk":
        raise ValueError(f"{platform_name}不使用Android NDK")
    try:
        return platform["ndks"][ndk_version]
    except KeyError as exc:
        raise ValueError(f"{platform_name}缺少NDK配置：{ndk_version}") from exc


def kdir_path(root, platform_name, target):
    return root / "kdir" / platform_name / target


def _quote(value):
    return shlex.quote(str(value))


def ensure_droid_ddk_root():
    """确保 /opt/droid-ddk 目录存在并归当前用户所有"""
    if not DROID_DDK_ROOT.is_dir():
        print("[+] 创建 /opt/droid-ddk ...")
        run(f"sudo mkdir -p {DROID_DDK_ROOT}")
    # 检查所有权
    import getpass, grp
    user = getpass.getuser()
    gid = os.getgid()
    group = grp.getgrgid(gid).gr_name
    stat = DROID_DDK_ROOT.stat()
    if stat.st_uid != os.getuid() or stat.st_gid != gid:
        print(f"[+] 修改 {DROID_DDK_ROOT} 所有者为 {user}:{group}")
        run(f"sudo chown -R {user}:{group} {DROID_DDK_ROOT}")


def extract_prebuilt(component, name, base_dir, prefix=""):
    """从 prebuilts 解压 tar.zst 到目标目录"""
    tarball = PREBUILTS_DIR / component / f"{prefix}{name}.tar.zst"
    if not tarball.is_file():
        print(f"[x] 预构建包不存在: {tarball}")
        sys.exit(1)
    dest = base_dir / name
    if dest.is_dir():
        print(f"[!] {name} already exists, skip")
        return
    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"[+] 解压 {tarball.name} -> {dest}")
    run(f"tar -xf {tarball} -C {base_dir}")


# ── clang ──────────────────────────────────────────────

def setup_clang_download(branch, version):
    dest = DROID_DDK_ROOT / "clang" / version
    if dest.is_dir():
        print(f"[!] {version} already exists, skip")
        return
    url = f"https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/refs/heads/{branch}/{version}.tar.gz"
    print(f"[+] Download from {url}")
    tarball = f"{version}.tar.gz"
    run(f"wget {url} -O {tarball}")
    dest.mkdir(parents=True, exist_ok=True)
    run(f"tar xzf {tarball} -C {dest}")
    os.remove(tarball)


def setup_clang_prebuilt(version):
    extract_prebuilt("clang", version, DROID_DDK_ROOT / "clang")


def download_verified(url, destination, expected_sha256):
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "droid-ddk"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected_sha256:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"NDK SHA-256不匹配：期望{expected_sha256}，实际{actual}")


def extract_archive(archive, destination, archive_type):
    destination = destination.resolve()
    if archive_type == "zip":
        with zipfile.ZipFile(archive) as package:
            members = package.infolist()
            for member in members:
                candidate = (destination / member.filename).resolve()
                if not candidate.is_relative_to(destination):
                    raise RuntimeError(f"归档包含越界路径：{member.filename}")
            package.extractall(destination)
            for member in members:
                mode = (member.external_attr >> 16) & 0o777
                if mode:
                    (destination / member.filename).chmod(mode)
        return
    if archive_type != "tar.gz":
        raise ValueError(f"不支持的NDK归档格式：{archive_type}")
    with tarfile.open(archive, "r:gz") as package:
        members = package.getmembers()
        for member in members:
            candidate = (destination / member.name).resolve()
            if not candidate.is_relative_to(destination):
                raise RuntimeError(f"归档包含越界路径：{member.name}")
        for member in members:
            package.extract(member, destination)


def setup_ndk(mapping, platform_name, ndk_version):
    spec = ndk_spec(mapping, platform_name, ndk_version)
    dest = DROID_DDK_ROOT / "ndk" / spec["root"]
    marker = dest / ".droid-ddk-toolchain.json"
    identity = {
        "release": spec["release"],
        "url": spec["url"],
        "sha256": spec["sha256"],
        "archiveType": spec["archiveType"],
    }
    if marker.is_file():
        try:
            if json.loads(marker.read_text()) == identity:
                print(f"[!] NDK {spec['version']} already exists, skip")
                return dest
        except json.JSONDecodeError:
            pass
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    download_dir = DROID_DDK_ROOT / ".downloads"
    archive = download_dir / spec["archive"]
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
        print(f"[+] Download NDK from {spec['url']}")
        download_verified(spec["url"], archive, spec["sha256"])
        extract_archive(archive, dest.parent, spec["archiveType"])
    finally:
        archive.unlink(missing_ok=True)
    if not dest.is_dir():
        raise RuntimeError(f"NDK归档未生成预期目录：{dest}")
    marker.write_text(json.dumps(identity, indent=2) + "\n")
    return dest


def arm64_rust_env():
    env = os.environ.copy()
    rustup_home = DROID_DDK_ROOT / ".rustup"
    cargo_home = DROID_DDK_ROOT / ".cargo"
    droid_ddk_bin = DROID_DDK_ROOT / "bin"
    env["RUSTUP_HOME"] = str(rustup_home)
    env["CARGO_HOME"] = str(cargo_home)
    env["RUSTUP_NO_SELF_UPDATE"] = "1"
    env["PATH"] = f"{droid_ddk_bin}:{cargo_home / 'bin'}:{env['PATH']}"
    return env


def arm64_rust_spec(mapping, platform_name, rust_version=None):
    spec = platform_config(mapping, platform_name).get("rust")
    if not spec:
        return None
    if not rust_version:
        return spec
    toolchains = spec.get("toolchains", {})
    if rust_version in toolchains:
        return toolchains[rust_version]
    if spec.get("version") == rust_version.removeprefix("rust-"):
        return spec
    raise ValueError(f"ARM64 Rust配置缺失：{rust_version}")


def setup_arm64_rust(mapping, platform_name, rust_version=None):
    spec = arm64_rust_spec(mapping, platform_name, rust_version)
    if not spec:
        return None
    env = arm64_rust_env()
    rustup = DROID_DDK_ROOT / ".cargo" / "bin" / "rustup"
    if not rustup.is_file():
        run("curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs | sh -s -- -y --no-modify-path", env=env)
    rustup_cmd = _quote(rustup)
    version = spec["version"]
    components = ",".join(spec["components"])
    run(f"{rustup_cmd} toolchain install {version} --profile minimal --component {components}", env=env)
    bindgen = DROID_DDK_ROOT / ".cargo" / "bin" / "bindgen"
    if not bindgen.is_file():
        run(
            f"{_quote(DROID_DDK_ROOT / '.cargo' / 'bin' / 'cargo')} +{version} install "
            f"bindgen-cli --version {spec['bindgenVersion']} --locked",
            env=env,
        )
    ensure_arm64_bindgen_wrapper()
    return arm64_rust_tools(mapping, platform_name, rust_version)


def ensure_arm64_bindgen_wrapper():
    """创建不继承目录形式CLANG_PATH的bindgen包装器。"""
    cargo_bindgen = DROID_DDK_ROOT / ".cargo" / "bin" / "bindgen"
    if not cargo_bindgen.is_file():
        raise RuntimeError("bindgen未安装，请先运行setup-toolchain")
    wrapper = DROID_DDK_ROOT / "bin" / "bindgen"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(
        "#!/bin/sh\n"
        "# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)\n"
        "unset CLANG_PATH\n"
        f"exec {_quote(cargo_bindgen)} \"$@\"\n"
    )
    wrapper.chmod(0o755)
    return wrapper


def arm64_rust_tools(mapping, platform_name, rust_version=None):
    spec = arm64_rust_spec(mapping, platform_name, rust_version)
    if not spec:
        return {}
    env = arm64_rust_env()
    rustup = DROID_DDK_ROOT / ".cargo" / "bin" / "rustup"
    cargo = DROID_DDK_ROOT / ".cargo" / "bin" / "cargo"
    cargo_bindgen = DROID_DDK_ROOT / ".cargo" / "bin" / "bindgen"
    if not rustup.is_file() or not cargo.is_file() or not cargo_bindgen.is_file():
        raise RuntimeError("ARM64 Rust工具链未安装，请先运行setup-toolchain")
    bindgen = ensure_arm64_bindgen_wrapper()
    version = spec["version"]
    rustc = Path(capture(f"{_quote(rustup)} which --toolchain {version} rustc", env=env))
    rustfmt = Path(capture(f"{_quote(rustup)} which --toolchain {version} rustfmt", env=env))
    sysroot = Path(capture(f"{_quote(rustc)} --print sysroot", env=env))
    rust_src = sysroot / "lib" / "rustlib" / "src" / "rust" / "library"
    if not rust_src.is_dir():
        raise RuntimeError(f"Rust源码组件缺失：{rust_src}")
    return {
        "env": env,
        "rustc": rustc,
        "rustfmt": rustfmt,
        "bindgen": bindgen,
        "rust_src": rust_src,
    }


# ── rust ───────────────────────────────────────────────

def setup_rust_download(version, branch, repo):
    ver_num = version.removeprefix("rust-")
    dest = DROID_DDK_ROOT / "rust" / version
    if dest.is_dir():
        print(f"[!] {version} already exists, skip")
        return
    # platform/prebuilts/rust (旧仓库) 需要额外拼 linux-x86 子路径
    if repo == "platform/prebuilts/rust":
        archive_path = f"linux-x86/{ver_num}"
    else:
        archive_path = ver_num
    url = f"https://android.googlesource.com/{repo}/+archive/refs/heads/{branch}/{archive_path}.tar.gz"
    print(f"[+] Download from {url}")
    tarball = f"{version}.tar.gz"
    run(f"wget {url} -O {tarball}")
    dest.mkdir(parents=True, exist_ok=True)
    run(f"tar xzf {tarball} -C {dest}")
    os.remove(tarball)


def setup_rust_prebuilt(version):
    extract_prebuilt("rust", version, DROID_DDK_ROOT / "rust")


# ── src ────────────────────────────────────────────────

def setup_source_download(name, branch=None):
    if not branch:
        branch = name
    dest = DROID_DDK_ROOT / "src" / name
    if dest.is_dir():
        print(f"[!] {name} already exists, skip")
        return
    print(f"[+] Clone {name} (branch: {branch})")
    run(f"git clone https://android.googlesource.com/kernel/common -b {branch} --depth 1 {dest}")
    modpost = dest / "scripts" / "mod" / "modpost.c"
    if modpost.is_file():
        run(f"sed -i 's/^\\(\\s*check_exports(mod);\\)/\\/\\/\\1/' {modpost}")
        run(f"sed -i 's/^\\(\\s*s->module = exp->module;\\)/\\/\\/\\1/' {modpost}")


def setup_source_prebuilt(name):
    extract_prebuilt("src", name, DROID_DDK_ROOT / "src", prefix="src.")


# ── build ──────────────────────────────────────────────

def _drain_output(proc, tag):
    """后台线程：持续消费进程剩余输出"""
    for line in proc.stdout:
        sys.stdout.write(f"[{tag}] {line}")
    sys.stdout.flush()


def toolchain_bin(mapping, platform_name, clang_version, ndk_version=None):
    platform = platform_config(mapping, platform_name)
    if platform["toolchainKind"] == "aosp-clang":
        return DROID_DDK_ROOT / "clang" / clang_version / "bin"
    if not ndk_version:
        raise ValueError(f"{platform_name}构建缺少NDK版本")
    spec = ndk_spec(mapping, platform_name, ndk_version)
    return DROID_DDK_ROOT / "ndk" / spec["root"] / spec["bin"]


def kernel_make_command(env, args):
    """将会被内核 Makefile 覆盖的工具变量作为命令行变量传入。"""
    assignments = []
    for name in ("RUSTC", "RUSTFMT", "BINDGEN", "RUST_LIB_SRC", "HOSTCFLAGS"):
        value = env.get(name)
        if value:
            assignments.append(f"{name}={_quote(value)}")
    prefix = " ".join(["make", *assignments])
    return f"{prefix} {args}"


def _make_kernel_env(
    mapping,
    platform_name,
    clang_version,
    rust_version=None,
    ndk_version=None,
    kernel_host_cflags=None,
):
    """构造内核编译所需的环境变量"""
    platform = platform_config(mapping, platform_name)
    clang_bin = toolchain_bin(mapping, platform_name, clang_version, ndk_version)
    if not clang_bin.is_dir():
        raise RuntimeError(f"工具链目录不存在：{clang_bin}")
    env = os.environ.copy()
    path_parts = [str(clang_bin)]
    if platform["toolchainKind"] == "aosp-clang":
        if rust_version:
            rust_bin = (DROID_DDK_ROOT / "rust" / rust_version / "bin").resolve()
            if rust_bin.is_dir():
                path_parts.append(str(rust_bin))
    else:
        libclang_path = platform.get("libclangPath")
        if platform_name == "linux-amd64":
            libclang_path = str(clang_bin.parent / "lib")
        if libclang_path:
            env["LIBCLANG_PATH"] = libclang_path
        host_cflags = " ".join(
            filter(None, (platform.get("hostCFlags"), kernel_host_cflags))
        )
        if host_cflags:
            env["HOSTCFLAGS"] = " ".join(filter(None, (env.get("HOSTCFLAGS"), host_cflags)))
        env.update({
            "CLANG_TRIPLE": "aarch64-linux-gnu-",
            "CC": str(clang_bin / "clang"),
            "LD": str(clang_bin / "ld.lld"),
            "AR": str(clang_bin / "llvm-ar"),
            "NM": str(clang_bin / "llvm-nm"),
            "OBJCOPY": str(clang_bin / "llvm-objcopy"),
            "OBJDUMP": str(clang_bin / "llvm-objdump"),
            "STRIP": str(clang_bin / "llvm-strip"),
            "HOSTCC": str(clang_bin / "clang"),
            "HOSTCXX": str(clang_bin / "clang++"),
        })
        if rust_version and platform_name == "linux-arm64":
            rust_tools = arm64_rust_tools(mapping, platform_name, rust_version)
            env.update(rust_tools["env"])
            path_parts.append(str(DROID_DDK_ROOT / ".cargo" / "bin"))
            env.update({
                "RUSTC": str(rust_tools["rustc"]),
                "RUSTFMT": str(rust_tools["rustfmt"]),
                "BINDGEN": str(rust_tools["bindgen"]),
                "RUST_LIB_SRC": str(rust_tools["rust_src"]),
            })
        elif rust_version:
            rust_bin = (DROID_DDK_ROOT / "rust" / rust_version / "bin").resolve()
            if not rust_bin.is_dir():
                raise RuntimeError(f"Rust工具链目录不存在：{rust_bin}")
            path_parts.append(str(rust_bin))
    path_parts.append(env["PATH"])
    env["PATH"] = ":".join(path_parts)
    env["CROSS_COMPILE"] = "aarch64-linux-gnu-"
    env["ARCH"] = "arm64"
    env["LLVM"] = "1"
    env["LLVM_IAS"] = "1"
    return env


def _configure_kernel(src_path, out_path_abs, env, lto=None, android_branch=None, require_rust=False):
    """defconfig + LTO 配置"""
    run(kernel_make_command(env, f"O={_quote(out_path_abs)} gki_defconfig"), cwd=src_path, env=env)

    scripts_config = src_path / "scripts" / "config"
    config_file = out_path_abs / ".config"
    if lto == "none":
        run(f"{scripts_config} --file {config_file} -d LTO_CLANG -e LTO_NONE -d LTO_CLANG_THIN -d LTO_CLANG_FULL -d THINLTO", env=env)
    elif lto == "thin":
        run(f"{scripts_config} --file {config_file} -e LTO_CLANG -d LTO_NONE -e LTO_CLANG_THIN -d LTO_CLANG_FULL -e THINLTO", env=env)
    elif lto == "full":
        run(f"{scripts_config} --file {config_file} -e LTO_CLANG -d LTO_NONE -d LTO_CLANG_THIN -e LTO_CLANG_FULL -d THINLTO", env=env)

    if android_branch == "android16-6.12":
        run(f"{scripts_config} --file {config_file} -e CFI_ICALL_NORMALIZE_INTEGERS", env=env)
    run(kernel_make_command(env, f"O={_quote(out_path_abs)} olddefconfig"), cwd=src_path, env=env)
    if require_rust:
        run(kernel_make_command(env, f"O={_quote(out_path_abs)} rustavailable"), cwd=src_path, env=env)


def build_kernel_start(
    mapping,
    platform_name,
    clang_version,
    android_branch,
    rust_version=None,
    ndk_version=None,
    kernel_host_cflags=None,
    lto=None,
    build_proc=None,
):
    """配置并启动内核编译，返回 (Popen, tag) 或 None（已跳过）"""
    out_path = kdir_path(DROID_DDK_ROOT, platform_name, android_branch)
    if out_path.is_dir():
        print(f"[!] {android_branch} already exists, skip")
        return None

    src_path = DROID_DDK_ROOT / "src" / android_branch
    if not src_path.is_dir():
        print(f"[x] 源码目录不存在: {src_path}")
        sys.exit(1)

    print(f"[+] Building {android_branch}")

    env = _make_kernel_env(
        mapping,
        platform_name,
        clang_version,
        rust_version,
        ndk_version,
        kernel_host_cflags,
    )
    out_path_abs = out_path.resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    _configure_kernel(
        src_path,
        out_path_abs,
        env,
        lto=lto,
        android_branch=android_branch,
        require_rust=rust_version is not None,
    )

    if build_proc is None:
        build_proc = os.cpu_count() or 1

    cmd = kernel_make_command(env, f"O={_quote(out_path_abs)} -j{build_proc}")
    print(f"  > {cmd}")
    proc = subprocess.Popen(
        cmd, shell=True, cwd=src_path, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    return proc, android_branch


def build_kernel_modules_prepare(
    mapping,
    platform_name,
    clang_version,
    android_branch,
    rust_version=None,
    ndk_version=None,
    kernel_host_cflags=None,
    lto=None,
    build_proc=None,
):
    """仅执行 modules_prepare（生成精简 kdir）"""
    out_path = kdir_path(DROID_DDK_ROOT, platform_name, android_branch)
    if out_path.is_dir():
        print(f"[!] {android_branch} already exists, skip modules_prepare")
        return

    src_path = DROID_DDK_ROOT / "src" / android_branch
    if not src_path.is_dir():
        print(f"[x] 源码目录不存在: {src_path}")
        sys.exit(1)

    print(f"[+] modules_prepare {android_branch}")

    env = _make_kernel_env(
        mapping,
        platform_name,
        clang_version,
        rust_version,
        ndk_version,
        kernel_host_cflags,
    )
    out_path_abs = out_path.resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    _configure_kernel(
        src_path,
        out_path_abs,
        env,
        lto=lto,
        android_branch=android_branch,
        require_rust=rust_version is not None,
    )

    if build_proc is None:
        build_proc = os.cpu_count() or 1

    run(kernel_make_command(env, f"O={_quote(out_path_abs)} modules_prepare"), cwd=src_path, env=env)


HEADER_SUFFIXES = {".h", ".hpp", ".hxx", ".h++", ".hh"}

# 构建外部内核模块所需的顶层文件
BUILD_FILES = [
    "Module.symvers",
    "vmlinux",
    "vmlinux.symvers",
    "System.map",
    "modules.order",
    "modules.builtin",
    "modules.builtin.modinfo",
]


def fix_kdir_min(kdir_full: Path, kdir_min: Path):
    """从完整构建目录拷贝缺失的头文件和构建文件到精简目录"""
    for kernel_full in sorted(kdir_full.iterdir()):
        if not kernel_full.is_dir():
            continue
        kernel_min = kdir_min / kernel_full.name
        if not kernel_min.is_dir():
            continue

        print(f"[+] 修补 kdir-min: {kernel_full.name}")

        # 拷贝构建文件
        for name in BUILD_FILES:
            src_file = kernel_full / name
            dst_file = kernel_min / name
            if not src_file.is_file() or dst_file.exists():
                continue
            shutil.copy2(src_file, dst_file)
            print(f"  复制构建文件: {name}")

        # 拷贝缺失的头文件
        header_copied = 0
        for src_file in kernel_full.rglob("*"):
            if not src_file.is_file():
                continue
            if src_file.suffix.lower() not in HEADER_SUFFIXES:
                continue
            rel = src_file.relative_to(kernel_full)
            dst_file = kernel_min / rel
            if dst_file.exists():
                continue
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            header_copied += 1
        print(f"  复制 {header_copied} 个头文件")


def build_kernels(mapping, platform_name, matrix_list, lto=None, build_proc=None):
    """流水线编译多个内核：检测到 LTO vmlinux 后立即启动下一个"""
    background_procs = []  # (proc, tag, thread)

    for i, item in enumerate(matrix_list):
        clang_ver = item.get("clang")
        android_ver = item.get("android")
        rust_ver = item.get("rust")
        ndk_ver = item.get("ndk")
        if not clang_ver or not android_ver:
            continue

        result = build_kernel_start(
            mapping,
            platform_name,
            clang_ver,
            android_ver,
            rust_version=rust_ver,
            ndk_version=ndk_ver,
            kernel_host_cflags=item.get("hostCFlags"),
            lto=lto or item.get("lto"),
            build_proc=build_proc,
        )
        if result is None:
            continue

        proc, tag = result
        is_last = (i == len(matrix_list) - 1)

        if is_last:
            # 最后一个：直接等待完成
            for line in proc.stdout:
                sys.stdout.write(f"[{tag}] {line}")
            sys.stdout.flush()
            proc.wait()
            if proc.returncode != 0:
                print(f"[x] {tag} 编译失败 (exit {proc.returncode})")
                sys.exit(proc.returncode)
        else:
            # 非最后一个：监控输出，检测到 LTO vmlinux 后启动下一个
            triggered = False
            for line in proc.stdout:
                sys.stdout.write(f"[{tag}] {line}")
                if not triggered and "LTO" in line and "vmlinux" in line:
                    print(f"[+] {tag} 已进入 LTO vmlinux 阶段，启动下一个构建")
                    triggered = True
                    break
            # 将剩余输出交给后台线程消费
            t = threading.Thread(target=_drain_output, args=(proc, tag), daemon=True)
            t.start()
            background_procs.append((proc, tag, t))

    # 等待所有后台构建完成
    failed = []
    for proc, tag, t in background_procs:
        t.join()
        proc.wait()
        if proc.returncode != 0:
            failed.append(tag)
            print(f"[x] {tag} 编译失败 (exit {proc.returncode})")

    if failed:
        print(f"[x] 以下构建失败: {', '.join(failed)}")
        sys.exit(1)


# ── 子命令 ─────────────────────────────────────────────

def filter_toolchains(mapping, platform_name, android_ver=None):
    """按宿主平台筛选目标，并提取其工具链版本。"""
    matrix_list = matrix_for_platform(mapping, platform_name, android_ver)
    if android_ver and not matrix_list:
        print(f"[x] {platform_name}不支持android版本: {android_ver}")
        sys.exit(1)
    clang_versions = {item["clang"] for item in matrix_list if item.get("clang")}
    rust_versions = {item["rust"] for item in matrix_list if item.get("rust")}
    clang_list = [c for c in mapping.get("clang", []) if c["version"] in clang_versions]
    rust_list = [r for r in mapping.get("rust", []) if r["version"] in rust_versions]
    return matrix_list, clang_list, rust_list


def resolve_platform(mapping, args):
    platform_name = args.host_platform or os.environ.get("DROID_DDK_PLATFORM")
    if platform_name is None:
        platform_name = host_platform()
    platform_config(mapping, platform_name)
    return platform_name


def cmd_setup_toolchain(args):
    mapping = load_mapping(args.map_file)
    ensure_droid_ddk_root()
    platform_name = resolve_platform(mapping, args)
    matrix_list, clang_list, rust_list = filter_toolchains(
        mapping, platform_name, args.android
    )
    if platform_config(mapping, platform_name)["toolchainKind"] == "android-ndk":
        ndk_versions = {item.get("ndk") for item in matrix_list}
        if None in ndk_versions:
            raise ValueError(f"{platform_name}目标缺少NDK版本")
        for ndk_version in sorted(ndk_versions):
            print(f"[+] Setup {platform_name} NDK {ndk_version}")
            setup_ndk(mapping, platform_name, ndk_version)
        if platform_name == "linux-arm64":
            for item in rust_list:
                print(f"[+] Setup ARM64 Rust {item['version']}")
                setup_arm64_rust(mapping, platform_name, item["version"])
        else:
            for item in rust_list:
                if args.source == "prebuilt":
                    setup_rust_prebuilt(item["version"])
                else:
                    setup_rust_download(item["version"], item["branch"], item["repo"])
        return
    print("[+] Setup clang")
    for item in clang_list:
        if args.source == "prebuilt":
            setup_clang_prebuilt(item["version"])
        else:
            setup_clang_download(item["branch"], item["version"])
    print("[+] Setup rust")
    for item in rust_list:
        if args.source == "prebuilt":
            setup_rust_prebuilt(item["version"])
        else:
            setup_rust_download(item["version"], item["branch"], item["repo"])


def cmd_setup_src(args):
    mapping = load_mapping(args.map_file)
    ensure_droid_ddk_root()
    platform_name = resolve_platform(mapping, args)
    matrix_list = matrix_for_platform(mapping, platform_name, args.android)
    if args.android and not matrix_list:
        print(f"[x] {platform_name}不支持android版本: {args.android}")
        sys.exit(1)
    supported = {item["android"] for item in matrix_list}
    android_list = [
        item for item in mapping.get("android", [])
        if item["name"] in supported
    ]
    print("[+] Setup kernel source")
    for item in android_list:
        if args.source == "prebuilt":
            setup_source_prebuilt(item["name"])
        else:
            setup_source_download(item["name"], item.get("branch"))


def cmd_build(args):
    """编译内核"""
    mapping = load_mapping(args.map_file)
    platform_name = resolve_platform(mapping, args)

    matrix_list = matrix_for_platform(mapping, platform_name, args.android)
    if args.android and not matrix_list:
        print(f"[x] {platform_name}不支持android版本: {args.android}")
        sys.exit(1)

    print("[+] Build kernel")
    build_kernels(mapping, platform_name, matrix_list, lto=args.lto, build_proc=args.jobs)

    if args.min:
        kdir = DROID_DDK_ROOT / "kdir" / platform_name
        kdir_full = DROID_DDK_ROOT / "kdir-full" / platform_name

        # mv kdir -> kdir-full
        if kdir.is_dir():
            if kdir_full.is_dir():
                shutil.rmtree(kdir_full)
            kdir_full.parent.mkdir(parents=True, exist_ok=True)
            print(f"[+] mv {kdir} -> {kdir_full}")
            kdir.rename(kdir_full)

        # 构建 modules_prepare -> kdir（精简版）
        for item in matrix_list:
            clang_ver = item.get("clang")
            android_ver = item.get("android")
            rust_ver = item.get("rust")
            if clang_ver and android_ver:
                build_kernel_modules_prepare(
                    mapping,
                    platform_name,
                    clang_ver,
                    android_ver,
                    rust_version=rust_ver,
                    ndk_version=item.get("ndk"),
                    kernel_host_cflags=item.get("hostCFlags"),
                    lto=args.lto or item.get("lto"),
                    build_proc=args.jobs,
                )

        # 从 kdir-full 修补 kdir
        fix_kdir_min(kdir_full, kdir)


def cmd_rebuild(args):
    if not DROID_DDK_ROOT.is_dir():
        print(f"[x] {DROID_DDK_ROOT} is not exist")
        sys.exit(1)

    mapping = load_mapping(args.map_file)
    platform_name = resolve_platform(mapping, args)

    kdir = DROID_DDK_ROOT / "kdir" / platform_name
    if kdir.is_dir():
        if args.android:
            target = kdir / args.android
            if target.is_dir():
                print(f"[+] Removing {target}")
                shutil.rmtree(target)
        else:
            for p in kdir.glob("android*"):
                print(f"[+] Removing {p}")
                shutil.rmtree(p)

    matrix_list = matrix_for_platform(mapping, platform_name, args.android)
    if args.android and not matrix_list:
        print(f"[x] {platform_name}不支持android版本: {args.android}")
        sys.exit(1)

    print("[+] Build kernel")
    build_kernels(mapping, platform_name, matrix_list, lto=args.lto, build_proc=args.jobs)


def add_common_args(parser):
    parser.add_argument("--map-file", type=Path,
                        default=Path(os.environ.get("MAP_FILE", str(DEFAULT_MAP_FILE))),
                        help="mapping.json 路径")
    parser.add_argument("--lto", choices=["none", "thin", "full"],
                        default=os.environ.get("LTO"),
                        help="LTO 模式")
    parser.add_argument("-j", "--jobs", type=int,
                        default=int(os.environ.get("BUILD_PROC", 0)) or None,
                        help="并行编译线程数")
    parser.add_argument("--host-platform", choices=["linux-amd64", "linux-arm64"],
                        default=None,
                        help="宿主工具链平台，默认由当前Linux主机架构决定")


def add_source_arg(parser):
    parser.add_argument("-s", "--source", choices=["download", "prebuilt"],
                        default="download",
                        help="来源：download (网络下载) 或 prebuilt (本地 prebuilts 解压)")


def add_android_arg(parser):
    parser.add_argument("--android", type=str, default=None,
                        help="仅操作指定的 android 版本 (如 android16-6.12)")


def main():
    parser = argparse.ArgumentParser(description="Droid DDK构建工具")
    sub = parser.add_subparsers(dest="command", required=True)

    # build - 编译内核
    p_build = sub.add_parser("build", help="编译内核")
    add_common_args(p_build)
    add_android_arg(p_build)
    p_build.add_argument("--min", action="store_true",
                         help="同时构建 kdir-min（modules_prepare + 修补头文件和构建文件）")

    # setup-toolchain - clang + rust
    p_tc = sub.add_parser("setup-toolchain", help="安装工具链 (clang + rust)")
    add_common_args(p_tc)
    add_source_arg(p_tc)
    add_android_arg(p_tc)

    # setup-src - 仅源码
    p_src = sub.add_parser("setup-src", help="仅安装内核源码")
    add_common_args(p_src)
    add_source_arg(p_src)
    add_android_arg(p_src)

    # rebuild - 重新编译
    p_rebuild = sub.add_parser("rebuild", help="清理并重新编译所有内核")
    add_common_args(p_rebuild)
    add_android_arg(p_rebuild)

    args = parser.parse_args()

    commands = {
        "build": cmd_build,
        "setup-toolchain": cmd_setup_toolchain,
        "setup-src": cmd_setup_src,
        "rebuild": cmd_rebuild,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
