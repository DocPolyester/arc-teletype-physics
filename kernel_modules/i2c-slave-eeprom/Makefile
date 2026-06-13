obj-m := i2c-slave-eeprom.o

KERNEL_SRC := /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KERNEL_SRC) M=$(PWD) modules

install:
	$(MAKE) -C $(KERNEL_SRC) M=$(PWD) modules_install
	depmod -a

clean:
	$(MAKE) -C $(KERNEL_SRC) M=$(PWD) clean
