LESS_FILES = $(shell find thinkhazard/static/less -type f -name '*.less' 2> /dev/null)
JS_FILES = $(shell find thinkhazard/static/js -type f -name '*.js' 2> /dev/null)
PY_FILES = $(shell find thinkhazard -type f -name '*.py' 2> /dev/null)
INSTANCEID ?= main

PKG_NAME ?= thinkhazard
PKG_PREFIX := /opt/c2c/gis/$(PKG_NAME)
PKG_DESC = "Think Hazard: Overcome Risk"
#PKG_VERSION ?= $(shell cd .build/pkg/venv/bin/ && ./python -c 'import pkg_resources; print(pkg_resources.get_distribution("thinkhazard").version)')
PKG_VERSION ?= $(shell date +%Y.%m.%d.%H.%M.%S)

.PHONY: all
all: help

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@echo
	@echo "- install                 Install thinkhazard"
	@echo "- build                   Build CSS and JS"
	@echo "- initdb-dev              Initialize db using development.ini"
	@echo "- initdb-prod             Initialize db using production.ini"
	@echo "- serve                   Run the dev server"
	@echo "- check                   Check the code with flake8, jshint and bootlint"
	@echo "- modwsgi                 Create files for Apache mod_wsgi"
	@echo "- test                    Run the unit tests"
	@echo "- dist                    Build a source distribution"
	@echo "- routes                  Show the application routes"
	@echo "- watch                   Run the build target when files in static dir change"
	@echo "- rpm                     Create RPM package"
	@echo "- deb                     Create DEB package"
	@echo

.PHONY: install
install: .build/requirements.timestamp .build/node_modules.timestamp

.PHONY: build
build: buildcss

.PHONY: buildcss
buildcss: thinkhazard/static/build/index.css \
	      thinkhazard/static/build/index.min.css \
	      thinkhazard/static/build/report.css \
	      thinkhazard/static/build/report.min.css \
	      thinkhazard/static/build/common.css \
	      thinkhazard/static/build/common.min.css

.PHONY: initdb-dev
initdb-dev:
	.build/venv/bin/initialize_thinkhazard_db development.ini

.PHONY: initdb-prod
initdb-prod:
	.build/venv/bin/initialize_thinkhazard_db production.ini

.PHONY: serve
serve: build
	.build/venv/bin/pserve --reload development.ini

.PHONY: routes
routes:
	.build/venv/bin/proutes development.ini

.PHONY: check
check: flake8 jshint bootlint

.PHONY: flake8
flake8: .build/dev-requirements.timestamp .build/flake8.timestamp

.PHONY: jshint
jshint: .build/node_modules.timestamp .build/jshint.timestamp

.PHONY: bootlint
bootlint: .build/node_modules.timestamp .build/bootlint.timestamp

.PHONY: modwsgi
modwsgi: install \
	     .build/thinkhazard-production.wsgi \
	     .build/thinkhazard-development.wsgi \
	     .build/apache-production.conf \
	     .build/apache-development.conf

.PHONY: test
test:
	.build/venv/bin/python setup.py test

.PHONY: dist
dist: .build/venv
	.build/venv/bin/python setup.py sdist

.PHONY: dbtunnel
dbtunnel:
	@echo "Opening tunnel…"
	ssh -N -L 9999:localhost:5432 wb-thinkhazard-dev-1.sig.cloud.camptocamp.net

.PHONY: watch
watch: .build/dev-requirements.timestamp
	@echo "Watching static files..."
	.build/venv/bin/nosier -p thinkhazard/static "make build"

.PHONY: rpm deb
rpm deb: build \
         .build/node_modules.timestamp \
         .build/bundle \
         .build/pkg/requirements.timestamp \
         .build/pkg/thinkhazard.wsgi \
         .build/pkg/apache.conf
	bundle exec fpm -f -s dir -t $@ -n $(PKG_NAME) -v $(PKG_VERSION) \
	--template-scripts --after-install packaging/after-install.sh \
	--description $(PKG_DESC) --prefix $(PKG_PREFIX) \
    node_modules production.ini .build/pkg/venv=. \
	.build/pkg/thinkhazard.wsgi=. .build/pkg/apache.conf=.

thinkhazard/static/build/%.min.css: $(LESS_FILES) .build/node_modules.timestamp
	mkdir -p $(dir $@)
	./node_modules/.bin/lessc --clean-css thinkhazard/static/less/$*.less $@

thinkhazard/static/build/%.css: $(LESS_FILES) .build/node_modules.timestamp
	mkdir -p $(dir $@)
	./node_modules/.bin/lessc thinkhazard/static/less/$*.less $@

.build/venv .build/pkg/venv:
	mkdir -p $(dir $@)
	virtualenv $@

.build/thinkhazard-%.wsgi: thinkhazard.wsgi
	sed 's#{{APP_INI_FILE}}#$(CURDIR)/$*.ini#' $< > $@
	chmod 755 $@

.build/pkg/thinkhazard.wsgi: thinkhazard.wsgi
	mkdir -p $(dir $@)
	sed 's#{{APP_INI_FILE}}#$(PKG_PREFIX)/production.ini#' $< > $@

.build/node_modules.timestamp: package.json
	mkdir -p $(dir $@)
	npm install
	touch $@

.build/dev-requirements.timestamp: .build/venv dev-requirements.txt
	mkdir -p $(dir $@)
	.build/venv/bin/pip install -r dev-requirements.txt > /dev/null 2>&1
	touch $@

.build/requirements.timestamp: .build/venv setup.py requirements.txt
	mkdir -p $(dir $@)
	.build/venv/bin/pip install -r requirements.txt
	touch $@

.build/pkg/requirements.timestamp: .build/pkg/venv setup.py
	mkdir -p $(dir $@)
	.build/pkg/venv/bin/pip install -r requirements.txt .
	touch $@

.build/flake8.timestamp: $(PY_FILES)
	mkdir -p $(dir $@)
	.build/venv/bin/flake8 $?
	touch $@

.build/jshint.timestamp: $(JS_FILES)
	mkdir -p $(dir $@)
	./node_modules/.bin/jshint --verbose $?
	touch $@

.build/bootlint.timestamp: $(JINJA2_FILES)
	mkdir -p $(dir $@)
	./node_modules/.bin/bootlint $?
	touch $@

.build/apache-%.conf: apache.conf .build/venv
	sed -e 's#{{PYTHONPATH}}#$(shell .build/venv/bin/python -c "import distutils; print(distutils.sysconfig.get_python_lib())")#' \
		-e 's#{{INSTANCEID}}#$(INSTANCEID)#g' \
		-e 's#{{WSGISCRIPT}}#$(abspath .build/thinkhazard-$*.wsgi)#' $< > $@

.build/pkg/apache.conf: apache.conf .build/pkg/venv
	sed -e 's#{{PYTHONPATH}}#$(PKG_PREFIX)/venv/lib/python2.7/site-packages#' \
		-e 's#{{INSTANCEID}}#main#g' \
		-e 's#{{WSGISCRIPT}}#$(PKG_PREFIX)/thinkhazard.wsgi#' $< > $@

.build/fonts.timestamp: .build/node_modules.timestamp
	mkdir -p thinkhazard/static/build/fonts
	cp node_modules/font-awesome/fonts/* thinkhazard/static/build/fonts/
	touch $@

.build/bundle:
	mkdir -p $(dir $@)
	bundle install --path $@

.PHONY: clean
clean:
	rm -f .build/thinkhazard-*.wsgi
	rm -f .build/apache-*.conf
	rm -f .build/flake8.timestamp
	rm -f .build/jshint.timestamp
	rm -f .build/booltlint.timestamp
	rm -f .build/pkg/thinkhazard.wsgi
	rm -f .build/pkg/apache.conf
	rm -f .build/pkg/requirements.timestamp
	rm -f *.deb
	rm -f *.rpm
	rm -rf thinkhazard/static/build

.PHONY: cleanall
cleanall:
	rm -rf .build
