# parts copied and adapted from a Makefile generated with
# gnome-doc-utils assistance
PKG_CONFIG          = pkg-config
INSTALL_DATA		= install -m 0644
LN					= ln -f
MKINSTALLDIRS		= install -d
XML2PO				= $(shell which xml2po)
XMLLINT				= $(shell which xmllint)
MSGMERGE			= $(shell which msgmerge)

OMF_DIR             = $(DATADIR)/omf
HELP_DIR            = $(DATADIR)/gnome/help

DOC_LINGUAS_EXCLUDE += C
DOC_LINGUAS = $(filter-out $(DOC_LINGUAS_EXCLUDE),$(notdir $(realpath $(filter %/,$(wildcard $(DOC_ABS_SRCDIR)/*/)))))

DOC_OMF_IN          = $(DOC_MODULE).omf.in
_DOC_OMF_IN			= $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_OMF_IN))
DOC_OMF_DB          = $(foreach locale,C $(DOC_LINGUAS),$(DOC_MODULE)-$(locale).omf)
_DOC_OMF_DB			= $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_OMF_DB))

DOC_OMF_ALL         = $(DOC_OMF_DB)
_DOC_OMF_ALL		= $(_DOC_OMF_DB)

DOC_C_MODULE        = C/$(DOC_MODULE).xml
_DOC_C_MODULE		= $(DOC_ABS_SRCDIR)/$(DOC_C_MODULE)
DOC_C_ENTITIES      = $(foreach ent,$(DOC_ENTITIES),C/$(ent))
_DOC_C_ENTITIES		= $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_C_ENTITIES))
DOC_C_INCLUDES      = $(foreach inc,$(DOC_INCLUDES),C/$(inc))
_DOC_C_INCLUDES		= $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_C_INCLUDES))
DOC_C_DOCS          = $(DOC_C_MODULE) $(DOC_C_ENTITIES) $(DOC_C_INCLUDES)
_DOC_C_DOCS			= $(_DOC_C_MODULE) $(_DOC_C_ENTITIES) $(_DOC_C_INCLUDES)
DOC_C_DOCS_NOENT    = $(DOC_C_MODULE) $(DOC_C_INCLUDES)
_DOC_C_DOCS_NOENT	= $(_DOC_C_MODULE) $(_DOC_C_INCLUDES)
DOC_C_FIGURES       = $(foreach fig,$(DOC_FIGURES),C/$(DOC_FIGURES_DIR)/$(fig))
_DOC_C_FIGURES      = $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_C_FIGURES]

DOC_POT             = $(DOC_MODULE).pot
_DOC_POT			= $(DOC_ABS_SRCDIR)/$(DOC_POT)
DOC_COMPLETE		= $(DOC_MODULE)-complete.xml
_DOC_COMPLETE		= $(DOC_ABS_SRCDIR)/C/$(DOC_COMPLETE)
DOC_POFILES         = $(foreach locale,$(DOC_LINGUAS),$(locale)/$(locale).po)
_DOC_POFILES		= $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_POFILES))
DOC_LC_MODULES      = $(foreach locale,$(DOC_LINGUAS),$(locale)/$(DOC_MODULE).xml)
_DOC_LC_MODULES		= $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_LC_MODULES))
DOC_LC_DOCS         = $(DOC_LC_MODULES)
_DOC_LC_DOCS		= $(_DOC_LC_MODULES)
DOC_LC_FIGURES      = $(foreach locale,$(DOC_LINGUAS),$(patsubst C/%,$(locale)/%,$(DOC_C_FIGURES)))
_DOC_LC_FIGURES		= $(patsubst %,$(DOC_ABS_SRCDIR)/%,$(DOC_LC_FIGURES))

SK_PKGDATADIR       = $(shell scrollkeeper-config --pkgdatadir)
SK_LOCALSTATEDIR	= $(shell scrollkeeper-config --pkglocalstatedir)
SK_CONTENTS_LIST    = $(SK_PKGDATADIR)/Templates/C/scrollkeeper_cl.xml

docbook2omf         = $(shell $(PKG_CONFIG) --variable db2omf gnome-doc-utils)

docbook2omf_args    = \
	--stringparam db2omf.basename $(DOC_MODULE)             \
	--stringparam db2omf.format $(3)                    \
	--stringparam db2omf.dtd                        \
	$(shell xmllint --valid --valid --valid --valid --valid --valid --valid --valid --valid --format $(2) | grep -h PUBLIC | head -n 1      \
	    | sed -e 's/.*PUBLIC \(\"[^\"]*\"\).*/\1/')         \
	--stringparam db2omf.lang $(notdir $(patsubst %/$(notdir $(2)),%,$(2))) \
	--stringparam db2omf.omf_dir "$(OMF_DIR)"               \
	--stringparam db2omf.help_dir "$(HELP_DIR)"             \
	--stringparam db2omf.omf_in "$(_DOC_OMF_IN)"                \
	--stringparam db2omf.scrollkeeper_cl "$(SK_CONTENTS_LIST)"        \
	$(docbook2omf) $(2)

po_diff_and_mv_or_rm  = \
	if [ ! -f '$(1)' ] || (diff '$(1)' '$(2)' | grep -v '^. "POT-Creation-Date:' | grep -q '^[<>] [^\#]'); then \
		echo 'Creating/updating '$$PWD'/$(1)'; \
		mv -f $(2) $(1); \
	else \
		echo 'Nothing to be done for '$$PWD'/$(1)'; \
		rm -f $(2); \
	fi

$(_DOC_OMF_DB) : $(_DOC_OMF_IN)
$(_DOC_OMF_DB) : $(DOC_ABS_SRCDIR)/$(DOC_MODULE)-%.omf : $(DOC_ABS_SRCDIR)/%/$(DOC_MODULE).xml
	@test -f "$(SK_CONTENTS_LIST)" || {   \
	  echo "The file '$(SK_CONTENTS_LIST)' does not exist." >&2;     \
	  echo "Please check your ScrollKeeper installation." >&2;      \
	  exit 1; }
	xsltproc -o $@ $(call docbook2omf_args,$@,$<,'docbook') || { rm -f "$@"; exit 1; }

$(_DOC_COMPLETE): $(_DOC_C_DOCS)
	$(XMLLINT) --postvalid --noblanks --noent --nsclean "$<" > "$@"

$(_DOC_POFILES): $(_DOC_POT) $(_DOC_COMPLETE)
	@if ! test -d $(dir $@); then \
		echo "mkdir $(dir $@)"; \
		mkdir "$(dir $@)"; \
	fi
	@if ! test -f $@; then \
		echo cp $(_DOC_POT) $@; \
		cp $(_DOC_POT) $@; \
	else \
		(cd $(dir $@) && \
			$(MSGMERGE) -o $(notdir $@).tmp $(notdir $@) $(_DOC_POT) >&/dev/null && \
			$(call po_diff_and_mv_or_rm,$(notdir $@),$(notdir $@).tmp)); \
	fi

$(_DOC_LC_DOCS) : $(_DOC_POFILES)
$(_DOC_LC_DOCS) : $(_DOC_COMPLETE)
	@(lang="$(notdir $(abspath $(dir $@)))"; cd $(dir $@) && \
		$(XML2PO) -e -p \
			"$(DOC_ABS_SRCDIR)/$$lang/$$lang.po" \
			"$(_DOC_COMPLETE)" > $(notdir $@).tmp && \
			cp $(notdir $@).tmp $(notdir $@) && rm -f $(notdir $@).tmp)

$(_DOC_POT): $(_DOC_COMPLETE)
	$(XML2PO) -e -o "$@.tmp" "$<" && \
		$(call po_diff_and_mv_or_rm,$@,$@.tmp)

doc-all:	$(_DOC_OMF_ALL)

doc-omf:	$(_DOC_OMF_ALL)

doc-po:		$(_DOC_POFILES)

doc-pot:	$(_DOC_POT)

doc-install:    $(_DOC_OMF_ALL) doc-install-docs doc-install-figures doc-install-omf

doc-install-docs:	$(_DOC_COMPLETE)
	@for locale in C $(DOC_LINGUAS); do \
	    echo "$(MKINSTALLDIRS) $(DESTDIR)$(HELP_DIR)/$(DOC_MODULE)/$$locale"; \
	    $(MKINSTALLDIRS) "$(DESTDIR)$(HELP_DIR)/$(DOC_MODULE)/$$locale"; \
		if [ "$$locale" = "C" ]; then \
		    fromdoc='C/$(DOC_COMPLETE)'; \
			todoc='C/$(DOC_MODULE).xml'; \
		else \
		    fromdoc="$$locale/$(DOC_MODULE).xml"; \
			todoc="$$fromdoc"; \
		fi; \
	    docdir="$(DESTDIR)$(HELP_DIR)/$(DOC_MODULE)/$$locale"; \
	    if ! test -d "$$docdir"; then \
	        echo "$(MKINSTALLDIRS) $$docdir"; \
	        $(MKINSTALLDIRS) "$$docdir"; \
	    fi; \
		rm -f "$(DOC_ABS_SRCDIR)/$$fromdoc.gz" || exit 1; \
		echo "$(INSTALL_DATA) $(DOC_ABS_SRCDIR)/$$fromdoc $(DESTDIR)$(HELP_DIR)/$(DOC_MODULE)/$$todoc"; \
		$(INSTALL_DATA) "$(DOC_ABS_SRCDIR)/$$fromdoc" "$(DESTDIR)$(HELP_DIR)/$(DOC_MODULE)/$$todoc" || exit 1; \
	done

doc-install-figures:
	@list='$(patsubst C/%,%,$(DOC_C_FIGURES))'; \
	for locale in C $(DOC_LINGUAS); do \
		for fig in $$list; do \
			moddir="$(DESTDIR)$(HELP_DIR)/$(DOC_MODULE)"; \
			figdir="$$moddir/$$locale"; \
			figdir2=`echo $$fig | sed -e 's/\/[^\/]*$$//'`; \
			if ! test -d "$$figdir/$$figdir2"; then \
				echo "$(MKINSTALLDIRS) $$figdir/$$figdir2"; \
				$(MKINSTALLDIRS) "$$figdir/$$figdir2"; \
			fi; \
			if test -f "$(DOC_ABS_SRCDIR)/$$locale/$$fig"; then \
				figfile="$(DOC_ABS_SRCDIR)/$$locale/$$fig"; \
				echo "$(INSTALL_DATA) $$figfile $$figdir/$$fig"; \
				$(INSTALL_DATA) "$$figfile" "$$figdir/$$fig"; \
			elif test -f "$(DOC_ABS_SRCDIR)/C/$$fig"; then \
				figfile="$$moddir/C/$$fig"; \
				echo $(LN) "$$figfile" "$$figdir/$$fig"; \
				$(LN) "$$figfile" "$$figdir/$$fig"; \
			fi; \
		done; \
	done

doc-install-omf:
	@$(MKINSTALLDIRS) $(DESTDIR)$(OMF_DIR)/$(DOC_MODULE)
	@list='$(DOC_OMF_ALL)'; for omf in $$list; do \
		echo "$(INSTALL_DATA) $(DOC_ABS_SRCDIR)/$$omf $(DESTDIR)$(OMF_DIR)/$(DOC_MODULE)/$$omf"; \
		$(INSTALL_DATA) $(DOC_ABS_SRCDIR)/$$omf $(DESTDIR)$(OMF_DIR)/$(DOC_MODULE)/$$omf; \
	done
	@echo "scrollkeeper-update -p $(DESTDIR)$(SK_LOCALSTATEDIR) -o $(DESTDIR)$(OMF_DIR)/$(DOC_MODULE)"
	@scrollkeeper-update -p "$(DESTDIR)$(SK_LOCALSTATEDIR)" -o "$(DESTDIR)$(OMF_DIR)/$(DOC_MODULE)"

doc-clean:
	rm -f $(_DOC_OMF_DB)
	rm -f $(_DOC_COMPLETE)
