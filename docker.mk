LESS_FILES = $(shell find thinkhazard/static/less -type f -name '*.less' 2> /dev/null)
JS_FILES = $(shell find thinkhazard/static/js -type f -name '*.js' 2> /dev/null)
PY_FILES = $(shell find thinkhazard -type f -name '*.py' 2> /dev/null)

-include local.mk

#########################
# Internal build target #
#########################

.PHONY: build
build: buildcss compile_catalog

.PHONY: buildcss
buildcss: \
		/opt/thinkhazard/thinkhazard/static/build/index.css \
		/opt/thinkhazard/thinkhazard/static/build/index.min.css \
		/opt/thinkhazard/thinkhazard/static/build/report.css \
		/opt/thinkhazard/thinkhazard/static/build/report.min.css \
		/opt/thinkhazard/thinkhazard/static/build/report_print.css \
		/opt/thinkhazard/thinkhazard/static/build/report_print.min.css \
		/opt/thinkhazard/thinkhazard/static/build/common.css \
		/opt/thinkhazard/thinkhazard/static/build/common.min.css \
		/opt/thinkhazard/thinkhazard/static/build/admin.css \
		/opt/thinkhazard/thinkhazard/static/build/admin.min.css \
		$(addprefix /opt/thinkhazard/thinkhazard/static/fonts/fontawesome-webfont., eot ttf woff woff2)

/opt/thinkhazard/thinkhazard/static/build/%.min.css: $(LESS_FILES)
	mkdir -p $(dir $@)
	lessc --include-path=${NODE_PATH} --clean-css thinkhazard/static/less/$*.less $@

/opt/thinkhazard/thinkhazard/static/build/%.css: $(LESS_FILES)
	mkdir -p $(dir $@)
	lessc --include-path=${NODE_PATH} thinkhazard/static/less/$*.less $@

.PRECIOUS: ${NODE_PATH}/font-awesome/fonts/fontawesome-webfont.%
${NODE_PATH}/font-awesome/fonts/fontawesome-webfont.%:
	touch -c $@

/opt/thinkhazard/thinkhazard/static/fonts/fontawesome-webfont.%: ${NODE_PATH}/font-awesome/fonts/fontawesome-webfont.%
	mkdir -p $(dir $@)
	cp $< $@


.PHONY: compile_catalog
compile_catalog: \
	/opt/thinkhazard/thinkhazard/locale/fr/LC_MESSAGES/thinkhazard.mo \
	/opt/thinkhazard/thinkhazard/locale/es/LC_MESSAGES/thinkhazard.mo

/opt/thinkhazard/thinkhazard/locale/%/LC_MESSAGES/thinkhazard.mo: thinkhazard/locale/%/LC_MESSAGES/thinkhazard.po
	mkdir -p $(dir $@)
	msgfmt -o $@ $<

thinkhazard/locale/%/LC_MESSAGES/thinkhazard.po: $(HOME)/.transifexrc
	tx pull --translations --languages=$* --resources=gfdrr-thinkhazard.ui --force
	touch `find thinkhazard/locale/ -name '*.po' 2> /dev/null`

.INTERMEDIATE: $(HOME)/.transifexrc
$(HOME)/.transifexrc:
	echo "[https://www.transifex.com]" > $@
	echo "rest_hostname = https://rest.api.transifex.com" >> $@
	@echo "token = $(TX_TOKEN)" >> $@
	cat $@


check: flake8 jshint

.PHONY: flake8
flake8:
	flake8 $(PY_FILES)

.PHONY: jshint
jshint:
	jshint --verbose $(JS_FILES)
