LESS_FILES = $(shell find thinkhazard/static/less -type f -name '*.less' 2> /dev/null)
JS_FILES = $(shell find thinkhazard/static/js -type f -name '*.js' 2> /dev/null)
PY_FILES = $(shell find thinkhazard -type f -name '*.py' 2> /dev/null)

-include local.mk

#########################
# Internal build target #
#########################

.PHONY: build
build: compile_catalog

.PHONY: compile_catalog
compile_catalog: \
	/opt/thinkhazard/thinkhazard/locale/fr/LC_MESSAGES/thinkhazard.mo \
	/opt/thinkhazard/thinkhazard/locale/es/LC_MESSAGES/thinkhazard.mo

/opt/thinkhazard/thinkhazard/locale/%/LC_MESSAGES/thinkhazard.mo: thinkhazard/locale/%/LC_MESSAGES/thinkhazard.po
	mkdir -p $(dir $@)
	msgfmt -o $@ $<

TX_BRANCH_DASHED := $(subst .,-,$(TX_BRANCH))

thinkhazard/locale/%/LC_MESSAGES/thinkhazard.po: $(HOME)/.transifexrc
	tx pull --translations --languages=$* --resources=gfdrr-thinkhazard.$(TX_BRANCH_DASHED)-ui --force
	touch `find thinkhazard/locale/ -name '*.po' 2> /dev/null`

.INTERMEDIATE: $(HOME)/.transifexrc
$(HOME)/.transifexrc:
	echo "[https://www.transifex.com]" > $@
	echo "rest_hostname = https://rest.api.transifex.com" >> $@
	@echo "token = $(TX_TOKEN)" >> $@
	cat $@

check: flake8

.PHONY: flake8
flake8:
	flake8 $(PY_FILES)
