CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2 -Isrc

test: build/test_bms_logic
	./build/test_bms_logic

build/test_bms_logic: src/bms_logic.c test/test_bms_logic.c src/bms_logic.h src/bms_config.h
	mkdir -p build
	$(CC) $(CFLAGS) -o $@ src/bms_logic.c test/test_bms_logic.c

clean:
	rm -rf build

.PHONY: test clean
