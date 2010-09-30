#License: GPL
#Copyright Red Hat Inc.  Oct 2006

PKGNAME=system-config-kdump
MODULENAME=system-config-kdump
VERSION=$(shell rpm -q --define 'dist %{nil}' --qf '%{version}\n' --specfile ${PKGNAME}.spec |head -1)
RELEASE=$(shell rpm -q --define 'dist %{nil}' --qf '%{release}\n' --specfile ${PKGNAME}.spec |head -1)
CVSTAG=$(PKGNAME)-$(subst .,_,$(VERSION)-$(RELEASE))
SUBDIRS=po

MANDIR=/usr/share/man
PREFIX=/usr
DATADIR=${PREFIX}/share
PKGDATADIR=${DATADIR}/${PKGNAME}
PKGIMAGESDIR=${PKGDATADIR}/images
ETC=/etc

PAMD_DIR        = ${ETC}/pam.d
SECURITY_DIR    = ${ETC}/security/console.apps

SERVICE_DIR  = ${DATADIR}/dbus-1/system-services
SERVICE_DATA = org.fedoraproject.systemconfig.kdump.mechanism.service

CONF_DIR  = ${ETC}/dbus-1/system.d
CONF_DATA = org.fedoraproject.systemconfig.kdump.mechanism.conf

POLICY_DIR  = ${DATADIR}/polkit-1/actions
POLICY_DATA = org.fedoraproject.systemconfig.kdump.policy

LIBEXEC_DIR     = ${PKGDATADIR}
LIBEXEC_SCRIPTS = system-config-kdump-backend.py

GLADE_DATA = *.glade
GLADE_DIR  = ${PKGDATADIR}

MAKEFILE        := $(lastword $(MAKEFILE_LIST))
TOPDIR          := $(abspath $(dir $(abspath $(MAKEFILE))))
DOC_ABS_SRCDIR  = $(TOPDIR)/help
DOC_MODULE      = system-config-kdump
DOC_FIGURES_DIR = figures
DOC_FIGURES     = basic.png expert.png filter.png target.png disabled.png enabled.png
DOC_ENTITIES    = distro-specifics.ent system-config-kdump-distro-specifics.ent system-config-kdump-abstract.xml system-config-kdump-content.xml

DESTDIR = $(INSTROOT)

default: subdirs py-build

subdirs: doc-all
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1; done

install: subdirs ${PKGNAME}.desktop doc-install py-install
	mkdir -p $(INSTROOT)/usr/bin
	mkdir -p $(INSTROOT)$(PKGDATADIR)
	mkdir -p $(INSTROOT)/usr/sbin
	mkdir -p $(INSTROOT)$(PAMD_DIR)
	mkdir -p $(INSTROOT)$(SECURITY_DIR)
	mkdir -p $(INSTROOT)$(PKGDATADIR)/pixmaps
	mkdir -p $(INSTROOT)/usr/share/applications
	mkdir -p $(INSTROOT)/usr/share/icons/hicolor/48x48/apps
	mkdir -p ${INSTROOT}${SERVICE_DIR}
	mkdir -p ${INSTROOT}${CONF_DIR}
	mkdir -p ${INSTROOT}${POLICY_DIR}
	mkdir -p ${INSTROOT}${LIBEXEC_DIR}
	mkdir -p ${INSTROOT}${GLADE_DIR}
	install -m0755 src/${PKGNAME}.py $(INSTROOT)$(PKGDATADIR)
	install src/${PKGNAME} $(INSTROOT)/usr/bin
	install -m644 src/${GLADE_DATA} $(INSTROOT)$(GLADE_DIR)
	install -m644 pixmaps/*.png $(INSTROOT)$(PKGDATADIR)/pixmaps
	install -m644 pixmaps/${PKGNAME}.png $(INSTROOT)/usr/share/icons/hicolor/48x48/apps
	install -m644 ${PKGNAME}.pam $(INSTROOT)$(PAMD_DIR)/${PKGNAME}
	install -m644 ${PKGNAME}.console $(INSTROOT)$(SECURITY_DIR)/${PKGNAME}
	install -m644 ${PKGNAME}.desktop $(INSTROOT)/usr/share/applications/${PKGNAME}.desktop
	install -m0755 src/${LIBEXEC_SCRIPTS} $(INSTROOT)${LIBEXEC_DIR}
	install -m0644 ${SERVICE_DATA} $(INSTROOT)${SERVICE_DIR}
	install -m0644 ${CONF_DATA} $(INSTROOT)${CONF_DIR}
	install -m0644 ${POLICY_DATA} $(INSTROOT)${POLICY_DIR}
#	ln -sf consolehelper $(INSTROOT)/usr/bin/${PKGNAME}
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

selinux-module:
	checkmodule -M -m -o local-system-config.mod local-system-config.te
	semodule_package -o local-system-config.pp -m local-system-config.mod
	semodule -i local-system-config.pp

local: clean
	@git log > ChangeLog
	@rm -rf ${PKGNAME}-$(VERSION).tar.bz2
	@rm -rf /tmp/${PKGNAME}-$(VERSION) /tmp/${PKGNAME}
	@dir=$$PWD; cd /tmp; cp -a $$dir ${PKGNAME}
	@mv /tmp/${PKGNAME} /tmp/${PKGNAME}-$(VERSION)
	@rm -rf /tmp/${PKGNAME}-${VERSION}/.git
	@dir=$$PWD; cd /tmp; tar --bzip2 -cSpf $$dir/${PKGNAME}-$(VERSION).tar.bz2 ${PKGNAME}-$(VERSION)
	@rm -rf /tmp/${PKGNAME}-$(VERSION)	
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.bz2"

clean: doc-clean py-clean
	@rm -fv *~
	@rm -fv src/*.pyc
	@rm -fv src/sckdump/*.pyc
	@rm -fv po/*mo po/*~ po/.depend
	@rm -fv ${PKGNAME}.desktop
	@rm -fv ChangeLog
	@rm -fv ${PKGNAME}*.tar.bz2

srpm:
	@echo Creating src.rpm
	@mkdir -p $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION)
	@mv $(PKGNAME)-$(VERSION).tar.bz2 $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION)/
	@cp $(PKGNAME).spec $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION)/
	@pushd $(HOME)/rpmbuild/$(PKGNAME)-$(VERSION) &> /dev/null ; rpmbuild --nodeps -bs $(PKGNAME).spec ; popd &> /dev/null
	@echo SRPM is: $(HOME)/rpmbuild/SRPMS/$(PKGNAME)-$(VERSION)-$(RELEASE).src.rpm

%.desktop: %.desktop.in
	@intltool-merge -d -u po/ $< $@

include doc_rules.mk
include py_rules.mk
