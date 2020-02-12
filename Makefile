LESS_FILES = $(shell find thinkhazard/static/less -type f -name '*.less' 2> /dev/null)
JS_FILES = $(shell find thinkhazard/static/js -type f -name '*.js' 2> /dev/null)
PY_FILES = $(shell find thinkhazard -type f -name '*.py' 2> /dev/null)
INSTANCEID ?= main
ifeq ($(INSTANCEID), main)
	INSTANCEPATH = /
	INSTANCEADMINPATH = /admin
else
	INSTANCEPATH = /$(INSTANCEID)
	INSTANCEADMINPATH = /$(INSTANCEID)/admin
endif
AUTHUSERFILE ?= /var/www/vhosts/wb-thinkhazard/conf/.htpasswd
DATA ?= world
INI_FILE ?= development.ini

.PHONY: all
all: help

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@echo
	@echo "- install                 Install thinkhazard"
	@echo "- buildcss                Build CSS"
	@echo "- populatedb              Populates database. Use DATA=turkey if you want to work with a sample data set"
	@echo "- initdb                  Initialize db using development.ini"
	@echo "- reinit_all              Completely clear and re-init database. Only for developement purpose."
	@echo "- import_admindivs        Import administrative divisions. Use DATA=turkey or DATA=indonesia if you want to work with a sample data set"
	@echo "- import_recommendations  Import recommendations"
	@echo "- harvest                 Harvest GeoNode layers metadata"
	@echo "- download                Download raster data from GeoNode"
	@echo "- complete                Mark complete hazardsets as such"
	@echo "- process                 Compute hazard levels from hazardsets for administrative divisions level 2"
	@echo "- decisiontree            Run the decision tree and perform upscaling"
	@echo "- publish                 Publish validated data on public web site"
	@echo "- serve_public            Run the dev server (public app)"
	@echo "- serve_admin             Run the dev server (admin app)"
	@echo "- check                   Check the code with flake8, jshint and bootlint"
	@echo "- test                    Run the unit tests"
	@echo "- dist                    Build a source distribution"
	@echo "- routes                  Show the application routes"
	@echo "- watch                   Run the build target when files in static dir change"
	@echo "- extract_messages        Extract translation string and update the .pot file"
	@echo "- transifex-push          Push translations to transifex"
	@echo "- transifex-pull          Pull translations from transifex"
	@echo "- transifex-import        Import po files into database"
	@echo "- compile_catalog         Compile language files"
	@echo

.PHONY: install
install: \
		.build/docker.timestamp \
		.build/node_modules.timestamp \
		.build/wkhtmltox \
		.build/phantomjs-2.1.1-linux-x86_64 \
		buildcss \
		compile_catalog

.PHONY: buildcss
buildcss: thinkhazard/static/build/index.css \
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

.PHONY: populatedb
populatedb: initdb import_admindivs import_recommendations import_contacts

.PHONY: reinit_all
reinit_all: initdb_force import_admindivs import_recommendations import_contacts harvest download complete process decisiontree

.PHONY: initdb
initdb:
	.build/venv/bin/initialize_thinkhazard_db $(INI_FILE)

.PHONY: initdb_force
initdb_force:
	.build/venv/bin/initialize_thinkhazard_db $(INI_FILE) --force=1

.PHONY: import_admindivs
import_admindivs: .build/requirements.timestamp \
		/tmp/thinkhazard/admindiv/$(DATA)/g2015_2014_0_upd270117.shp \
		/tmp/thinkhazard/admindiv/$(DATA)/g2015_2014_1_upd270117.shp \
		/tmp/thinkhazard/admindiv/$(DATA)/g2015_2014_2_upd270117.shp
	@while [ -z "$$CONTINUE" ]; do \
		read -r -p "This will remove all the existing data in the administrative divisions table. Continue? [y] " CONTINUE;  \
	done ; \
	[ $$CONTINUE = "y" ] || [ $$CONTINUE = "Y" ] || (echo "Exiting."; exit 1;)
	.build/venv/bin/import_admindivs $(INI_FILE) folder=/tmp/thinkhazard/admindiv/$(DATA)

/tmp/thinkhazard/admindiv/$(DATA)/%.shp: /tmp/thinkhazard/admindiv/$(DATA)/%.zip
	unzip -o $< -d /tmp/thinkhazard/admindiv/$(DATA)

/tmp/thinkhazard/admindiv/$(DATA)/%_upd270117.zip:
	mkdir -p $(dir $@)
	wget -nc "http://dev.camptocamp.com/files/thinkhazard/$(DATA)/$(notdir $@)" -O $@

.PHONY: import_recommendations
import_recommendations: .build/requirements.timestamp
	.build/venv/bin/import_recommendations $(INI_FILE)

.PHONY: import_contacts
import_contacts: .build/requirements.timestamp
	.build/venv/bin/import_contacts $(INI_FILE)

.PHONY: harvest
harvest: .build/requirements.timestamp
	.build/venv/bin/harvest -v

.PHONY: download
download: .build/requirements.timestamp
	.build/venv/bin/download -v

.PHONY: complete
complete: .build/requirements.timestamp
	.build/venv/bin/complete -v

.PHONY: process
process: .build/requirements.timestamp
	.build/venv/bin/process -v

.PHONY: decisiontree
decisiontree: .build/requirements.timestamp
	.build/venv/bin/decision_tree -v

.PHONY: publish
publish: .build/requirements.timestamp
	.build/venv/bin/publish $(INI_FILE)

.PHONY: transifex-import
transifex-import: .build/requirements.timestamp
	.build/venv/bin/importpo $(INI_FILE)

.build/docker.timestamp: thinkhazard development.ini production.ini setup.py Dockerfile requirements.txt
	mkdir -p $(dir $@)
	docker build -t camptocamp/thinkhazard .
	touch $@

.PHONY: docker_build
docker_build: .build/docker.timestamp

.PHONY: serve_public
serve_public: .build/docker.timestamp
	docker run -it --net=host --env-file=.env -v $(shell pwd):/app camptocamp/thinkhazard pserve --reload c2c://$(INI_FILE) -n public

.PHONY: serve_admin
serve_admin: install
	.build/venv/bin/pserve --reload $(INI_FILE) --app-name=admin

.PHONY: routes
routes:
	.build/venv/bin/proutes $(INI_FILE)

.PHONY: check
check: flake8 jshint bootlint

.PHONY: flake8
flake8: .build/dev-requirements.timestamp .build/flake8.timestamp

.PHONY: jshint
jshint: .build/node_modules.timestamp .build/jshint.timestamp

.PHONY: bootlint
bootlint: .build/node_modules.timestamp .build/bootlint.timestamp

.PHONY: test
test: 
	docker run -it --net=host --env-file=.env -v $(shell pwd):/app camptocamp/thinkhazard nosetests

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
	.build/venv/bin/nosier -p thinkhazard/static "make buildcss"

thinkhazard/static/build/%.min.css: $(LESS_FILES) .build/node_modules.timestamp
	mkdir -p $(dir $@)
	./node_modules/.bin/lessc --clean-css thinkhazard/static/less/$*.less $@

thinkhazard/static/build/%.css: $(LESS_FILES) .build/node_modules.timestamp
	mkdir -p $(dir $@)
	./node_modules/.bin/lessc thinkhazard/static/less/$*.less $@

.build/venv:
	mkdir -p $(dir $@)
	# make a first virtualenv to get a recent version of virtualenv
	virtualenv venv
	venv/bin/pip install virtualenv
	venv/bin/virtualenv .build/venv
	# remove the temporary virtualenv
	rm -rf venv

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
	.build/venv/bin/pip install numpy==1.10.1
	.build/venv/bin/pip install -r requirements.txt
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

.build/apache.timestamp: \
		.build/thinkhazard_public-production.wsgi \
		.build/thinkhazard_public-development.wsgi \
		.build/thinkhazard_admin-production.wsgi \
		.build/thinkhazard_admin-development.wsgi \
		.build/apache-production.conf \
		.build/apache-development.conf
	sudo apache2ctl graceful
	touch $@

.build/thinkhazard_public-%.wsgi: thinkhazard_public.wsgi
	mkdir -p $(dir $@)
	sed 's#{{APP_INI_FILE}}#$(CURDIR)/$*.ini#' $< > $@
	chmod 755 $@

.build/thinkhazard_admin-%.wsgi: thinkhazard_admin.wsgi
	mkdir -p $(dir $@)
	sed 's#{{APP_INI_FILE}}#$(CURDIR)/$*.ini#' $< > $@
	chmod 755 $@

.build/apache-%.conf: apache.conf .build/venv
	sed -e 's#{{PYTHONPATH}}#$(shell .build/venv/bin/python -c "import sys; print(sys.path[-1])")#' \
		-e 's#{{INSTANCEID}}#$(INSTANCEID)#g' \
		-e 's#{{INSTANCEPATH}}#$(INSTANCEPATH)#g' \
		-e 's#{{INSTANCEADMINPATH}}#$(INSTANCEADMINPATH)#g' \
		-e 's#{{AUTHUSERFILE}}#$(AUTHUSERFILE)#g' \
		-e 's#{{WSGISCRIPT}}#$(abspath .build/thinkhazard_public-$*.wsgi)#' \
		-e 's#{{WSGISCRIPT_ADMIN}}#$(abspath .build/thinkhazard_admin-$*.wsgi)#' $< > $@

.build/wkhtmltox:
	wget https://github.com/GFDRR/thinkhazard/releases/download/wkhtmltox/wkhtmltox-0.12.3_linux-generic-amd64.tar.xz && tar -xv -f wkhtmltox-0.12.3_linux-generic-amd64.tar.xz
	mv wkhtmltox .build

.build/phantomjs-2.1.1-linux-x86_64:
	wget https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2 && tar -jxf phantomjs-2.1.1-linux-x86_64.tar.bz2
	mv phantomjs-2.1.1-linux-x86_64 .build/

.PRECIOUS: node_modules/font-awesome/fonts/fontawesome-webfont.%
node_modules/font-awesome/fonts/fontawesome-webfont.%: .build/node_modules.timestamp
	touch -c $@

thinkhazard/static/fonts/fontawesome-webfont.%: node_modules/font-awesome/fonts/fontawesome-webfont.%
	mkdir -p $(dir $@)
	cp $< $@

.PHONY: clean
clean:
	rm -f .build/thinkhazard-*.wsgi
	rm -f .build/apache-*.conf
	rm -f .build/flake8.timestamp
	rm -f .build/jshint.timestamp
	rm -f .build/booltlint.timestamp
	rm -rf thinkhazard/static/build
	rm -f thinkhazard/static/fonts/FontAwesome.otf
	rm -f thinkhazard/static/fonts/fontawesome-webfont.*

.PHONY: cleanall
cleanall:
	rm -rf .build
	rm -rf node_modules

.PHONY: extract_messages
extract_messages:
	.build/venv/bin/pot-create -c lingua.cfg -o thinkhazard/locale/thinkhazard.pot thinkhazard/templates thinkhazard/dont_remove_me.enum-i18n
	.build/venv/bin/pot-create -c lingua.cfg -o thinkhazard/locale/thinkhazard-database.pot thinkhazard/dont_remove_me.db-i18n
	# removes the creation date to avoid unnecessary git changes
	sed -i '/^"POT-Creation-Date: /d' thinkhazard/locale/thinkhazard.pot

$(HOME)/.transifexrc:
	echo "[https://www.transifex.com]" > $@
	echo "hostname = https://www.transifex.com" >> $@
	echo "username = antoine.abt@camptocamp.com" >> $@
	echo "password = $(TX_PWD)" >> $@
	echo "token =" >> $@

.PHONY: transifex-push
transifex-push: $(HOME)/.transifexrc
	.build/venv/bin/tx push -s

.PHONY: transifex-pull
transifex-pull: $(HOME)/.transifexrc
	.build/venv/bin/tx pull

.PHONY: compile_catalog
compile_catalog: $(HOME)/.transifexrc transifex-pull
	msgfmt -o thinkhazard/locale/fr/LC_MESSAGES/thinkhazard.mo thinkhazard/locale/fr/LC_MESSAGES/thinkhazard.po
	msgfmt -o thinkhazard/locale/es/LC_MESSAGES/thinkhazard.mo thinkhazard/locale/es/LC_MESSAGES/thinkhazard.po
