SHELL := /bin/bash 
VENVDIR := $(shell mktemp -ud)
PKGDIR := $(shell mktemp -ud)
GITREV := $(shell git rev-parse --verify --short HEAD)
PACKAGENAME := karactrl-$(GITREV).tar.gz
prefix := /opt/hacklab/karactrl


.PHONY: clean all
all: package

dist/karactrl: karactrl.py karactrl.spec requirements.txt
	virtualenv --system-site-packages -p `which python3` $(VENVDIR)
	source $(VENVDIR)/bin/activate ; pip install -r requirements_dev.txt
	source $(VENVDIR)/bin/activate ; pyinstaller --clean --onefile karactrl.spec
	rm -rf $(VENVDIR)

install: dist/karactrl
	mkdir -p $(prefix)
	cp -r karactrl_config.json.example dist/karactrl templates h264-live-player $(prefix)
	echo "$(GITREV)" >$(prefix)/version.txt

package: dist/karactrl karactrl_config.json.example
	mkdir $(PKGDIR)
	cp -r karactrl_config.json.example dist/karactrl templates h264-live-player $(PKGDIR)/
	pushd $(PKGDIR) ; tar -cvzf /tmp/$(PACKAGENAME) ./ ; popd ; mv /tmp/$(PACKAGENAME) ./
	rm -rf $(PKGDIR)

clean:
	rm -rf build/ dist/

