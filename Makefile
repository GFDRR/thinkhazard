LESS_FILES = $(shell find thinkhazard/static/less -type f -name '*.less' 2> /dev/null)
JS_FILES = $(shell find thinkhazard/static/js -type f -name '*.js' 2> /dev/null)
PY_FILES = $(shell find thinkhazard -type f -name '*.py' 2> /dev/null)

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
	@echo "- watchless               Watch less files"
	@echo

.PHONY: install
install: setup-develop .build/node_modules.timestamp
	
.PHONY: setup-develop
setup-develop: .build/venv
	.build/venv/bin/python setup.py develop

.PHONY: build
build: buildcss

.PHONY: buildcss
buildcss: thinkhazard/static/build/index.css \
	      thinkhazard/static/build/index.min.css \
	      thinkhazard/static/build/report.css \
	      thinkhazard/static/build/report.min.css

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
flake8: .build/requirements.timestamp .build/flake8.timestamp

.PHONY: jshint
jshint: .build/node_modules.timestamp .build/jshint.timestamp

.PHONY: bootlint
bootlint: .build/node_modules.timestamp .build/bootlint.timestamp

.PHONY: modwsgi
modwsgi: install .build/venv/thinkhazard.wsgi .build/apache.conf

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

.PHONY: watchless
watchless: .build/requirements.timestamp
	@echo "Watching less files…"
	.build/venv/bin/nosier -p thinkhazard/static/less "make thinkhazard/static/build/index.css thinkhazard/static/build/report.css"

thinkhazard/static/build/%.min.css: $(LESS_FILES) .build/node_modules.timestamp
	mkdir -p $(dir $@)
	./node_modules/.bin/lessc --clean-css thinkhazard/static/less/$*.less $@

thinkhazard/static/build/%.css: $(LESS_FILES) .build/node_modules.timestamp
	mkdir -p $(dir $@)
	./node_modules/.bin/lessc thinkhazard/static/less/$*.less $@

.build/venv:
	mkdir -p $(dir $@)
	virtualenv --no-site-packages .build/venv

.build/venv/thinkhazard.wsgi: thinkhazard.wsgi
	sed 's#{{DIR}}#$(CURDIR)#' $< > $@
	chmod 755 $@

.build/node_modules.timestamp: package.json
	mkdir -p $(dir $@)
	npm install
	touch $@

.build/requirements.timestamp: .build/venv requirements.txt
	mkdir -p $(dir $@)
	.build/venv/bin/pip install -r requirements.txt > /dev/null 2>&1
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

.build/apache.conf: apache.conf .build/venv
	sed -e 's#{{PYTHONPATH}}#$(shell .build/venv/bin/python -c "import distutils; print(distutils.sysconfig.get_python_lib())")#' \
		-e 's#{{WSGISCRIPT}}#$(abspath .build/venv/thinkhazard.wsgi)#' $< > $@

.PHONY: clean
clean:
	rm -f .build/venv/thinkhazard.wsgi
	rm -f .build/apache.conf
	rm -rf thinkhazard/static/build

.PHONY: cleanall
cleanall:
	rm -rf .build
