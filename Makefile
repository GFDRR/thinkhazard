export TX_BRANCH = 3.0

AUTHUSERFILE ?= /var/www/vhosts/wb-thinkhazard/conf/.htpasswd
DATA ?= world

-include local.mk

export INI_FILE ?= c2c://development.ini

export PGHOST ?= db
export PGHOST_SLAVE ?= db
export PGPORT ?= 5432

export PGDATABASE_PUBLIC ?= thinkhazard
export PGUSER_PUBLIC ?= thinkhazard
export PGPASSWORD_PUBLIC ?= thinkhazard

export PGDATABASE_ADMIN ?= thinkhazard_admin
export PGUSER_ADMIN ?= thinkhazard
export PGPASSWORD_ADMIN ?= thinkhazard

export GEONODE_URL ?= https://www.geonode-gfdrrlab.org
export GEONODE_USERNAME ?= geonode
export GEONODE_API_KEY ?= geonode

export AWS_ENDPOINT_URL ?= http://minio:9000/
export AWS_ACCESS_KEY_ID ?= minioadmin
export AWS_SECRET_ACCESS_KEY ?= minioadmin
export AWS_BUCKET_NAME ?= thinkhazard

export ANALYTICS ?= DO-NOT-TRACK

export TX_USR ?= tx_usr
export TX_PWD ?= tx_pwd

export BROKER_URL ?= redis://redis:6379/0

export HTPASSWORDS ?= admin:admin

export PUPPETEER_URL ?= http://puppeteer:8080

TEST ?= tests

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

DOCKER_CMD=docker compose -f docker-compose-test.yaml run --rm --user `id -u` -p '5680:5680' test

DOCKER_MAKE_CMD=$(DOCKER_CMD) make -f docker.mk

.PHONY: build
build: ## Build docker images
build: .env
	docker compose build

.PHONY: check
check: ## Check the code with flake8, jshint and bootlint
check:
	$(DOCKER_MAKE_CMD) check

.PHONY: buildcss
buildcss: ## Build css files
buildcss:
	$(DOCKER_MAKE_CMD) buildcss

.PHONY: compile_catalog
compile_catalog: ## Compile language files
compile_catalog:
	$(DOCKER_MAKE_CMD) compile_catalog

.PHONY: test
test: ## Run automated tests
	# $(DOCKER_CMD) nosetests -v
	$(DOCKER_CMD) pytest -vv --cov=thinkhazard $(TEST)

.PHONY: test-debug
test-debug: ## Run automated tests
	$(DOCKER_CMD) python3 \
	-m debugpy --listen "0.0.0.0:5680" --wait-for-client \
	-m pytest -vv $(TEST)

.PHONY: bash
test-bash: ## Open bash in a test container
	$(DOCKER_CMD) bash

.PHONY: test-psql
test-psql: ## Run psql in local thinkhazard_test database
	docker compose -f docker-compose-test.yaml exec testdb psql -U thinkhazard -d thinkhazard_test

.PHONY: clean
clean:
	rm -rf thinkhazard/static/build
	rm -rf thinkhazard/static/fonts
	rm -rf `find thinkhazard/locale -name *.po 2> /dev/null`
	rm -rf `find thinkhazard/locale -name *.mo 2> /dev/null`
	docker compose down --remove-orphans

.PHONY: cleanall
cleanall: clean
	docker compose down -v --remove-orphans
	docker rmi -f \
		camptocamp/thinkhazard \
		camptocamp/thinkhazard-builder \
		camptocamp/thinkhazard-testdb

.PHONY: .env
.env:
	rm -f .env
	cat .env.tmpl | envsubst > .env

#######################
# Build docker images #
#######################

.PHONY: docker_build_thinkhazard
docker_build_thinkhazard:
	docker build \
		--no-cache \
		--progress plain \
		--build-arg TX_TOKEN=${TX_TOKEN} \
		--target app \
		-t camptocamp/thinkhazard \
		.

####################################
# Push to docker hub and transifex #
####################################

.PHONY: docker-push
docker-push: ## Push images to docker hub
	./scripts/docker-push

.PHONY: transifex-push-ui
transifex-push-ui: ## Push UI strings to transifex
transifex-push-ui: initdb
	docker compose run --rm thinkhazard /app/thinkhazard/scripts/tx-push-ui

.PHONY: transifex-push-db
transifex-push-db: ## Push database strings to transifex
	docker compose run --rm thinkhazard /app/thinkhazard/scripts/tx-push-db

.PHONY: transifex-pull-db
transifex-pull-db: ## Pull database strings from transifex
	docker compose run --rm thinkhazard /app/thinkhazard/scripts/tx-pull-db


##############
# Processing #
##############

.PHONY: publish
publish: ## Publish validated data on public web site (for prod: make -f prod.mk publish)
	docker compose run --rm thinkhazard publish -v


#######################
# Initialize database #
#######################

.PHONY: populatedb
populatedb: ## Populates database. Example: GPKG=path_to_geopackage_file make populatedb
populatedb: initdb import_admindivs import_recommendations import_contacts

.PHONY: initdb
initdb: ## Initialize database model
	docker compose run --rm thinkhazard python -m thinkhazard.scripts.initializedb "$(INI_FILE)#admin"

.PHONY: alembic_upgrade
alembic_upgrade: ## Upgrade database model
	docker compose run --rm thinkhazard alembic -n admin -n public upgrade head

.PHONY: initdb_force
initdb_force:
	docker compose run --rm thinkhazard initialize_thinkhazard_db "$(INI_FILE)#admin" --force=1

.PHONY: reinit_all
reinit_all: ## Completely clear and re-init database. Only for developement purpose. Example: GPKG=path_to_geopackage_file make reinit_all
reinit_all: initdb_force import_admindivs import_recommendations import_contacts

.PHONY: psql
psql: ## Run psql in local thinkhazard database
	docker compose exec db psql -U thinkhazard -d thinkhazard

.PHONY: bash
bash: ## Open bash in an app container
	docker compose run --rm --user `id -u` thinkhazard bash

.PHONY: import_admindivs
import_admindivs: ## Import administrative divisions. Example: GPKG=path_to_geopackage_file make import_admindivs
import_admindivs:
	docker compose run --rm -v $(GPKG):/tmp/file.gpkg thinkhazard import_geopackage -v --geopackage-path /tmp/file.gpkg

.PHONY: import_recommendations
import_recommendations: ## Import recommendations
	docker compose run --rm thinkhazard import_recommendations -v

.PHONY: import_contacts
import_contacts: ## Import contacts
	docker compose run --rm thinkhazard import_contacts -v


#############################
# Backup / restore database #
#############################

export LOCAL_BACKUP_FOLDER ?= /tmp
export BACKUP ?= thinkhazard_admin.`date "+%Y-%m-%d"`.backup

psql-admin:  # Run psql on int/prod admin databases, example: make -f config/prod.mk psql
	docker run --rm -ti --entrypoint "" \
		-e PGHOST=$(PGHOST_SLAVE) \
		-e PGPORT=$(PGPORT_SLAVE) \
		-e PGUSER=$(PGUSER_ADMIN) \
		-e PGPASSWORD=$(PGPASSWORD_ADMIN) \
		camptocamp/postgres:12 \
		psql -d $(PGDATABASE_ADMIN)

restore:  # Restore database backup in local database
	docker compose up -d db

	# Drop and restore schemas datamart and processing
	docker compose exec --user postgres db psql -d $(PGDATABASE_ADMIN) \
		-c "DROP SCHEMA IF EXISTS datamart CASCADE; CREATE SCHEMA datamart AUTHORIZATION $(PGUSER_ADMIN);"
	docker compose exec --user postgres db psql -d $(PGDATABASE_ADMIN) \
		-c "DROP SCHEMA IF EXISTS processing CASCADE; CREATE SCHEMA processing AUTHORIZATION $(PGUSER_ADMIN);"
	cat $(LOCAL_BACKUP_FOLDER)/${BACKUP} | \
		docker exec -i \
			-e PGHOST=localhost \
			-e PGPORT=$(PGPORT_SLAVE) \
			-e PGUSER=$(PGUSER_ADMIN) \
			-e PGPASSWORD=$(PGPASSWORD_ADMIN) \
			thinkhazard_db_1 \
		pg_restore \
			--no-owner \
			-d $(PGDATABASE_ADMIN) -n datamart -n processing

	# Drop and restore table alembic_version
	docker compose exec --user postgres db psql -d $(PGDATABASE_ADMIN) \
		-c "DROP TABLE IF EXISTS alembic_version;"
	cat $(LOCAL_BACKUP_FOLDER)/${BACKUP} | \
		docker exec -i \
			-e PGHOST=localhost \
			-e PGPORT=$(PGPORT_SLAVE) \
			-e PGUSER=$(PGUSER_ADMIN) \
			-e PGPASSWORD=$(PGPASSWORD_ADMIN) \
			thinkhazard_db_1 \
		pg_restore \
			--no-owner \
			-d $(PGDATABASE_ADMIN) -n public -t alembic_version


.PHONY: routes
routes:
	.build/venv/bin/proutes $(INI_FILE)


.PHONY: dbtunnel
dbtunnel:
	@echo "Opening tunnel…"
	ssh -N -L 9999:localhost:5432 wb-thinkhazard-dev-1.sig.cloud.camptocamp.net


.PHONY: watch
watch: .build/dev-requirements.timestamp
	@echo "Watching static files..."
	.build/venv/bin/nosier -p thinkhazard/static "make buildcss"


