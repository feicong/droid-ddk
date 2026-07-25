// Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)
#include <linux/init.h>
#include <linux/module.h>

static int __init droid_ddk_validation_init(void) {
	return 0;
}

static void __exit droid_ddk_validation_exit(void) {
}

module_init(droid_ddk_validation_init);
module_exit(droid_ddk_validation_exit);
MODULE_DESCRIPTION("Droid DDK ARM64 validation module");
MODULE_LICENSE("GPL");
