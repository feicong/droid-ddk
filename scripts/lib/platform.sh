#!/usr/bin/env bash
# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

droid_ddk_normalize_machine() {
    case "$1" in
        x86_64|amd64)
            printf '%s\n' linux-amd64
            ;;
        aarch64|arm64)
            printf '%s\n' linux-arm64
            ;;
        *)
            printf '不支持的Linux宿主架构：%s\n' "$1" >&2
            return 2
            ;;
    esac
}

droid_ddk_host_platform() {
    droid_ddk_normalize_machine "$(uname -m)"
}

droid_ddk_normalize_platform() {
    case "$1" in
        linux-amd64|linux/amd64)
            printf '%s\n' linux-amd64
            ;;
        linux-arm64|linux/arm64)
            printf '%s\n' linux-arm64
            ;;
        *)
            printf '不支持的平台：%s\n' "$1" >&2
            return 2
            ;;
    esac
}

droid_ddk_docker_platform() {
    case "$1" in
        linux-amd64)
            printf '%s\n' linux/amd64
            ;;
        linux-arm64)
            printf '%s\n' linux/arm64
            ;;
        *)
            printf '不支持的平台：%s\n' "$1" >&2
            return 2
            ;;
    esac
}

droid_ddk_artifact_platform() {
    case "$1" in
        linux-amd64|linux-arm64)
            printf '%s\n' "$1"
            ;;
        *)
            printf '不支持的产物平台：%s\n' "$1" >&2
            return 2
            ;;
    esac
}
