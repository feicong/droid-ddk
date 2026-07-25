# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)

JQ := $(shell command -v jq 2>/dev/null)
ifeq ($(JQ),)
  $(error "jq 未安装，请先安装 jq 以解析 $(ROOT)/mapping.json")
endif

BINDGEN_VER := $(shell jq -r '.platforms["linux-arm64"].rust.bindgenVersion' $(ROOT)/mapping.json)

REG ?= docker.io/fsx199
IMG ?= droid-ddk
PUSH ?= 0
FORCE ?= 0
PLAT ?= linux/arm64
PLATFORMS ?= $(PLAT)
BUILDKIT ?= 1
DOCKER ?= docker
HOST_PLATFORM ?= $(if $(filter linux/arm64,$(PLAT)),linux-arm64,linux-amd64)
MATRIX := $(shell jq -r --arg platform "$(HOST_PLATFORM)" '.matrix[] | select(.platforms | index($$platform)) | "\(.android):\(.clang):\(.rust // ""):\(.ndk // "")"' $(ROOT)/mapping.json | tr '\n' ' ')

BUILDER_IMAGE := $(REG)/droid-ddk-builder:latest
TOOLCHAIN_IMAGE := $(REG)/droid-ddk-toolchain
MIN_IMAGE := $(REG)/droid-ddk-min
DATE := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
REV := $(shell git -C $(ROOT) rev-parse HEAD)

ifeq ($(PUSH),1)
  BUILD_OUTPUT := --platform $(PLATFORMS) --push
else
  BUILD_OUTPUT := --platform $(PLAT) --load
endif

.PHONY: list builder toolchains build build-all build-min build-min-all push push-all push-min push-min-all push-toolchains

list:
	@for i in $(MATRIX); do echo $$i; done

builder:
	@echo "==> Building $(BUILDER_IMAGE) for $(if $(filter 1,$(PUSH)),$(PLATFORMS),$(PLAT))"
	DOCKER_BUILDKIT=$(BUILDKIT) $(DOCKER) buildx build $(BUILD_OUTPUT) \
	  -f $(ROOT)/docker/ddk-builder/Dockerfile \
	  -t $(BUILDER_IMAGE) $(ROOT)

toolchains:
	@for pair in $(MATRIX); do \
	  ANDROID=$$(echo $$pair | cut -d: -f1); \
	  CLANG=$$(echo $$pair | cut -d: -f2); \
	  RUST=$$(echo $$pair | cut -d: -f3); \
	  NDK=$$(echo $$pair | cut -d: -f4); \
	  if [ -z "$$NDK" ]; then echo "NDK not found for $$ANDROID on $(HOST_PLATFORM)"; exit 2; fi; \
	  NDK_URL=$$(jq -r --arg platform "$(HOST_PLATFORM)" --arg ndk "$$NDK" '.platforms[$$platform].ndks[$$ndk].url' $(ROOT)/mapping.json); \
	  NDK_SHA256=$$(jq -r --arg platform "$(HOST_PLATFORM)" --arg ndk "$$NDK" '.platforms[$$platform].ndks[$$ndk].sha256' $(ROOT)/mapping.json); \
	  NDK_ROOT=$$(jq -r --arg platform "$(HOST_PLATFORM)" --arg ndk "$$NDK" '.platforms[$$platform].ndks[$$ndk].root' $(ROOT)/mapping.json); \
	  NDK_ARCHIVE_TYPE=$$(jq -r --arg platform "$(HOST_PLATFORM)" --arg ndk "$$NDK" '.platforms[$$platform].ndks[$$ndk].archiveType' $(ROOT)/mapping.json); \
	  KERNEL_HOSTCFLAGS=$$(jq -r --arg android "$$ANDROID" '.matrix[] | select(.android == $$android) | .hostCFlags // ""' $(ROOT)/mapping.json); \
	  if [ "$$NDK_URL" = "null" ] || [ "$$NDK_SHA256" = "null" ] || [ "$$NDK_ROOT" = "null" ] || [ "$$NDK_ARCHIVE_TYPE" = "null" ]; then echo "NDK configuration missing for $$NDK on $(HOST_PLATFORM)"; exit 2; fi; \
	  NDK_ARGS="--build-arg NDK_VERSION=$$NDK --build-arg NDK_URL=$$NDK_URL --build-arg NDK_SHA256=$$NDK_SHA256 --build-arg NDK_ROOT=$$NDK_ROOT --build-arg NDK_ARCHIVE_TYPE=$$NDK_ARCHIVE_TYPE"; \
	  if [ "$(FORCE)" = "1" ] || ! $(DOCKER) image inspect $(TOOLCHAIN_IMAGE):$$ANDROID >/dev/null 2>&1; then \
	    echo "==> Building $(TOOLCHAIN_IMAGE):$$ANDROID for $(if $(filter 1,$(PUSH)),$(PLATFORMS),$(PLAT))"; \
	    DOCKER_BUILDKIT=$(BUILDKIT) $(DOCKER) buildx build $(BUILD_OUTPUT) \
	      --build-arg BUILDER_IMAGE=$(BUILDER_IMAGE) \
	      --build-arg CLANG_VER=$$CLANG \
	      --build-arg RUST_VER=$$RUST \
	      --build-arg BINDGEN_VER=$(BINDGEN_VER) \
	      --build-arg KERNEL_HOSTCFLAGS="$$KERNEL_HOSTCFLAGS" \
	      $$NDK_ARGS \
	      -f $(ROOT)/docker/ddk-toolchain/Dockerfile \
	      -t $(TOOLCHAIN_IMAGE):$$ANDROID $(ROOT) || exit $$?; \
	  fi; \
	done

push-toolchains:
	@for pair in $(MATRIX); do \
	  ANDROID=$${pair%%:*}; \
	  $(DOCKER) push $(TOOLCHAIN_IMAGE):$$ANDROID || exit $$?; \
	done

build:
	@if [ -z "$(VER)" ]; then echo "Usage: make build VER=<androidX-Y>"; exit 1; fi
	@ENTRY=$$(echo "$(MATRIX)" | tr ' ' '\n' | grep "^$(VER):"); \
	CLANG=$$(echo $$ENTRY | cut -d: -f2); \
	RUST=$$(echo $$ENTRY | cut -d: -f3); \
	if [ -z "$$CLANG" ]; then echo "CLANG not found for $(VER)"; exit 2; fi; \
	echo "==> Building $(REG)/$(IMG):$(VER)"; \
	DOCKER_BUILDKIT=$(BUILDKIT) $(DOCKER) buildx build $(BUILD_OUTPUT) \
	  --build-arg TOOLCHAIN_IMAGE=$(TOOLCHAIN_IMAGE):$(VER) \
	  --build-arg CLANG_VER=$$CLANG \
	  --build-arg RUST_VER=$$RUST \
	  --build-arg ANDROID_VER=$(VER) \
	  --build-arg VERSION=$(VER) \
	  --build-arg REVISION=$(REV) \
	  --build-arg CREATED=$(DATE) \
	  -f $(ROOT)/docker/ddk/Dockerfile \
	  -t $(REG)/$(IMG):$(VER) $(ROOT)

build-all:
	@for pair in $(MATRIX); do \
	  VER=$${pair%%:*}; \
	  $(MAKE) build VER=$$VER || exit $$?; \
	done

build-min:
	@if [ -z "$(VER)" ]; then echo "Usage: make build-min VER=<androidX-Y>"; exit 1; fi
	@ENTRY=$$(echo "$(MATRIX)" | tr ' ' '\n' | grep "^$(VER):"); \
	CLANG=$$(echo $$ENTRY | cut -d: -f2); \
	RUST=$$(echo $$ENTRY | cut -d: -f3); \
	if [ -z "$$CLANG" ]; then echo "CLANG not found for $(VER)"; exit 2; fi; \
	echo "==> Building $(MIN_IMAGE):$(VER)"; \
	DOCKER_BUILDKIT=$(BUILDKIT) $(DOCKER) buildx build $(BUILD_OUTPUT) \
	  --build-arg TOOLCHAIN_IMAGE=$(TOOLCHAIN_IMAGE):$(VER) \
	  --build-arg CLANG_VER=$$CLANG \
	  --build-arg RUST_VER=$$RUST \
	  --build-arg ANDROID_VER=$(VER) \
	  --build-arg VERSION=$(VER) \
	  --build-arg REVISION=$(REV) \
	  --build-arg CREATED=$(DATE) \
	  -f $(ROOT)/docker/ddk-min/Dockerfile \
	  -t $(MIN_IMAGE):$(VER) $(ROOT)

build-min-all:
	@for pair in $(MATRIX); do \
	  VER=$${pair%%:*}; \
	  $(MAKE) build-min VER=$$VER || exit $$?; \
	done

push:
	@if [ -z "$(VER)" ]; then echo "Usage: make push VER=<androidX-Y>"; exit 1; fi
	$(DOCKER) push $(REG)/$(IMG):$(VER)

push-all:
	@for pair in $(MATRIX); do \
	  VER=$${pair%%:*}; \
	  $(MAKE) push VER=$$VER || exit $$?; \
	done

push-min:
	@if [ -z "$(VER)" ]; then echo "Usage: make push-min VER=<androidX-Y>"; exit 1; fi
	$(DOCKER) push $(MIN_IMAGE):$(VER)

push-min-all:
	@for pair in $(MATRIX); do \
	  VER=$${pair%%:*}; \
	  $(MAKE) push-min VER=$$VER || exit $$?; \
	done
