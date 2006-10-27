#License: GPL
#Copyright Red Hat Inc.  Oct 2006

PKGNAME=system-config-kdump
MODULENAME=system-config-kdump
VERSION=$(shell rpm -q --qf '%{version}\n' --specfile ${PKGNAME}.spec |head -1)
RELEASE=$(shell rpm -q --qf '%{release}\n' --specfile ${PKGNAME}.spec |head -1)
CVSTAG=r$(subst .,-,$(VERSION))
SUBDIRS=po

MANDIR=/usr/share/man
PREFIX=/usr
DATADIR=${PREFIX}/share
PKGDATADIR=${DATADIR}/${PKGNAME}
PKGIMAGESDIR=${PKGDATADIR}/images

PAMD_DIR        = /etc/pam.d
SECURITY_DIR    =/etc/security/console.apps

default: subdirs

subdirs:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1; done

install: ${PKGNAME}.desktop
	mkdir -p $(INSTROOT)/usr/bin
	mkdir -p $(INSTROOT)$(PKGDATADIR)
	mkdir -p $(INSTROOT)/usr/sbin
	mkdir -p $(INSTROOT)$(PAMD_DIR)
	mkdir -p $(INSTROOT)$(SECURITY_DIR)
	mkdir -p $(INSTROOT)$(PKGDATADIR)/pixmaps
	mkdir -p $(INSTROOT)/usr/share/applications
	mkdir -p $(INSTROOT)/usr/share/icons/hicolor/48x48/apps
	install -m644 src/*.py $(INSTROOT)$(PKGDATADIR)
	install src/${PKGNAME} $(INSTROOT)$(PKGDATADIR)/${PKGNAME}
	install -m644 src/system-config-kdump.glade $(INSTROOT)$(PKGDATADIR)
	install -m644 pixmaps/*.png $(INSTROOT)$(PKGDATADIR)/pixmaps
	install -m644 pixmaps/${PKGNAME}.png $(INSTROOT)/usr/share/icons/hicolor/48x48/apps
	install -m644 ${PKGNAME}.pam $(INSTROOT)$(PAMD_DIR)/${PKGNAME}
	install -m644 ${PKGNAME}.console $(INSTROOT)$(SECURITY_DIR)/${PKGNAME}
	install -m644 ${PKGNAME}.desktop $(INSTROOT)/usr/share/applications/${PKGNAME}.desktop
	ln -sf consolehelper $(INSTROOT)/usr/bin/${PKGNAME}
	for d in $(SUBDIRS); do \
	(cd $$d; $(MAKE) INSTROOT=$(INSTROOT) MANDIR=$(MANDIR) install) \
		|| case "$(MFLAGS)" in *k*) fail=yes;; *) exit 1;; esac; \
	done && test -z "$$fail"

force-tag:
	cvs tag -cFR $(CVSTAG) .

archive: 
	cvs tag -cFR $(CVSTAG) .
	@rm -rf /tmp/${PKGNAME}-$(VERSION) /tmp/${PKGNAME}
	@CVSROOT=`cat CVS/Root`; cd /tmp; cvs -d $$CVSROOT export -r$(CVSTAG) ${MODULENAME}
	@mv /tmp/${MODULENAME} /tmp/${PKGNAME}-$(VERSION)
	@dir=$$PWD; cd /tmp; tar --bzip2 -cSpf $$dir/${PKGNAME}-$(VERSION).tar.bz2 ${PKGNAME}-$(VERSION)
	@rm -rf /tmp/${PKGNAME}-$(VERSION)
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.bz2"

snapsrc: archive
	@rpmbuild -ta $(PKGNAME)-$(VERSION).tar.bz2

local: clean
	@rm -rf ${PKGNAME}-$(VERSION).tar.bz2
	@rm -rf /tmp/${PKGNAME}-$(VERSION) /tmp/${PKGNAME}
	@dir=$$PWD; cd /tmp; cp -a $$dir ${PKGNAME}
	@mv /tmp/${PKGNAME} /tmp/${PKGNAME}-$(VERSION)
	@dir=$$PWD; cd /tmp; tar --bzip2 -cSpf $$dir/${PKGNAME}-$(VERSION).tar.bz2 ${PKGNAME}-$(VERSION)
	@rm -rf /tmp/${PKGNAME}-$(VERSION)	
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.bz2"

clean:
	@rm -fv *~
	@rm -fv src/*.pyc
	@rm -fv ${PKGNAME}.desktop

srpm:
	@echo Creating src.rpm
	@mkdir -p $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION)
	@mv $(PKGNAME)-$(VERSION).tar.bz2 $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION)/
	@cp $(PKGNAME).spec $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION)/
	@pushd $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION) &> /dev/null ; rpmbuild --nodeps -bs $(PKGNAME).spec ; popd &> /dev/null
	@echo SRPM is: $(HOME)/rpmbuild/SRPMS/$(PKGNAME)-$(VERSION)-$(RELEASE).src.rpm

%.desktop: %.desktop.in
	@intltool-merge -d -u po/ $< $@
