# Copyright (c) 2025-2026 fei_cong(https://github.com/feicong/feicong-course)

obj-m += hello.o

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
