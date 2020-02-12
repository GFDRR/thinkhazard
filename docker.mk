
LESS_FILES = $(shell find thinkhazard/static/less -type f -name '*.less' 2> /dev/null)
JS_FILES = $(shell find thinkhazard/static/js -type f -name '*.js' 2> /dev/null)
PY_FILES = $(shell find thinkhazard -type f -name '*.py' 2> /dev/null)

#########################
# Internal build target #
#########################

.PHONY: build
build: buildcss compile_catalog

.PHONY: buildcss
buildcss: \
		thinkhazard/static/build/index.css \
		thinkhazard/static/build/index.min.css \
		thinkhazard/static/build/report.css \
		thinkhazard/static/build/report.min.css \
		thinkhazard/static/build/report_print.css \
		thinkhazard/static/build/report_print.min.css \
		thinkhazard/static/build/common.css \
		thinkhazard/static/build/common.min.css \
		thinkhazard/static/build/admin.css \
		thinkhazard/static/build/admin.min.css \
		$(addprefix thinkhazard/static/fonts/fontawesome-webfont., eot ttf woff woff2)

thinkhazard/static/build/%.min.css: $(LESS_FILES)
	mkdir -p $(dir $@)
	/app/node_modules/.bin/lessc --clean-css thinkhazard/static/less/$*.less $@

thinkhazard/static/build/%.css: $(LESS_FILES)
	mkdir -p $(dir $@)
	/app/node_modules/.bin/lessc thinkhazard/static/less/$*.less $@

.PRECIOUS: node_modules/font-awesome/fonts/fontawesome-webfont.%
node_modules/font-awesome/fonts/fontawesome-webfont.%:
	touch -c $@

thinkhazard/static/fonts/fontawesome-webfont.%: node_modules/font-awesome/fonts/fontawesome-webfont.%
	mkdir -p $(dir $@)
	cp $< $@


.PHONY: compile_catalog
compile_catalog: transifex-pull
	msgfmt -o thinkhazard/locale/fr/LC_MESSAGES/thinkhazard.mo thinkhazard/locale/fr/LC_MESSAGES/thinkhazard.po
	msgfmt -o thinkhazard/locale/es/LC_MESSAGES/thinkhazard.mo thinkhazard/locale/es/LC_MESSAGES/thinkhazard.po

.PHONY: transifex-pull
transifex-pull: $(HOME)/.transifexrc
	tx pull

$(HOME)/.transifexrc:
	echo "[https://www.transifex.com]" > $@
	echo "hostname = https://www.transifex.com" >> $@
	echo "username = $(TX_USR)" >> $@
	echo "password = $(TX_PWD)" >> $@
	echo "token =" >> $@


check: flake8 jshint bootlint

.PHONY: flake8
flake8:
	flake8 $(PY_FILES)

.PHONY: jshint
jshint:
	./node_modules/.bin/jshint --verbose $(JS_FILES)

.PHONY: bootlint
bootlint:
	./node_modules/.bin/bootlint $(JINJA2_FILES)
