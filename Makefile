
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

-include local.mk

.PHONY: help_old
help_old:
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

default: help

.PHONY: help
help: ## Display this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "    %-20s%s\n", $$1, $$2}'


################
# Entry points #
################

.PHONY: build
build: ## Build docker images
build: docker_build_thinkhazard docker_build_builder docker_build_testdb

.PHONY: check
check: ## Check the code with flake8, jshint and bootlint
check:
	docker-compose -f docker-compose-build.yaml run --rm test make -f docker.mk check

.PHONY: test
test: ## Run the unit tests
	docker-compose -f docker-compose-build.yaml run --rm test nosetests -v


#######################
# Build docker images #
#######################

.PHONY: docker_build_thinkhazard
docker_build_thinkhazard:
	docker build \
		--build-arg TX_USR=${TX_USR} \
		--build-arg TX_PWD=${TX_PWD} \
		--target app -t camptocamp/thinkhazard .

.PHONY: docker_build_builder
docker_build_builder:
	docker build \
		--build-arg TX_USR=${TX_USR} \
		--build-arg TX_PWD=${TX_PWD} \
		--target builder -t camptocamp/thinkhazard-builder .

.PHONY: docker_build_testdb
docker_build_testdb:
	docker build -t camptocamp/thinkhazard-testdb docker/testdb



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

.PHONY: docker_buildcss
docker_buildcss:
	docker run -it --net=host --env-file=.env -v $(shell pwd):/app camptocamp/thinkhazard-builder make buildcss

.PHONY: serve_public
serve_public: build
	docker-compose up thinkhazard

.PHONY: serve_admin
serve_admin: install
	docker-compose up thinkhazard_admin

.PHONY: routes
routes:
	.build/venv/bin/proutes $(INI_FILE)

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

.PHONY: transifex-push
transifex-push: $(HOME)/.transifexrc
	.build/venv/bin/tx push -s


