# License: GPLv2+
# Simple Makefile rules for setup and install of system-config-kdump
#

PY_SETUP_IN = setup.py.in
PY_CONFIG_IN = src/sckdump/config.py.in

PY_SETUP = setup.py
PY_CONFIG = src/sckdump/config.py

INSTROOT ?= /

$(PY_SETUP): $(PY_SETUP_IN)
	sed -e "s/@VERSION@/$(VERSION)/g" < $< > $@

$(PY_CONFIG): $(PY_CONFIG_IN)
	sed -e "s/@VERSION@/$(VERSION)/g" < $< > $@

py-install: $(PY_SETUP) $(PY_CONFIG)
	python $(PY_SETUP) install --skip-build --root $(INSTROOT)

py-clean: $(PY_SETUP) $(PY_CONFIG)
	python $(PY_SETUP) clean
	rm $(PY_SETUP) $(PY_CONFIG)
	rm -rf build

py-build: $(PY_SETUP) $(PY_CONFIG)
	python $(PY_SETUP) build

