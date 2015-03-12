.PHONY: all
all: help

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Possible targets:"
	@echo
	@echo "- install                 Install thinkhazard"
	@echo "- initdb                  (Re-)initialize the database"
	@echo "- serve                   Run the dev server"
	@echo "- check                   Check the code with flake8"
	@echo "- modwsgi                 Create files for Apache mod_wsgi"
	@echo "- test                    Run the unit tests"
	@echo "- dist                    Build a source distribution"
	@echo "- routes                  Show the application routes"
	@echo

.PHONY: install
install: setup-develop .build/node_modules.timestamp
	
.PHONY: setup-develop
setup-develop: .build/venv
	.build/venv/bin/python setup.py develop

.PHONY: initdb
initdb:
	.build/venv/bin/initialize_thinkhazard_db development.ini

.PHONY: serve
serve:
	.build/venv/bin/pserve --reload development.ini

.PHONY: routes
routes:
	.build/venv/bin/proutes development.ini

.PHONY: check
check: flake8

.PHONY: flake8
flake8: .build/venv/bin/flake8
	.build/venv/bin/flake8 thinkhazard

.PHONY: modwsgi
modwsgi: install .build/venv/thinkhazard.wsgi .build/apache.conf

.PHONY: test
test:
	.build/venv/bin/python setup.py test

.PHONY: dist
dist: .build/venv
	.build/venv/bin/python setup.py sdist

.build/venv:
	mkdir -p $(dir $@)
	virtualenv --no-site-packages .build/venv

.build/venv/bin/flake8: .build/venv
	.build/venv/bin/pip install -r requirements.txt > /dev/null 2>&1

.build/venv/thinkhazard.wsgi: thinkhazard.wsgi
	sed 's#{{DIR}}#$(CURDIR)#' $< > $@
	chmod 755 $@

.build/node_modules.timestamp: package.json
	mkdir -p $(dir $@)
	npm install
	touch $@

.build/apache.conf: apache.conf .build/venv
	sed -e 's#{{PYTHONPATH}}#$(shell .build/venv/bin/python -c "import distutils; print(distutils.sysconfig.get_python_lib())")#' \
		-e 's#{{WSGISCRIPT}}#$(abspath .build/venv/thinkhazard.wsgi)#' $< > $@

.PHONY: clean
clean:
	rm -f .build/venv/thinkhazard.wsgi
	rm -f .build/apache.conf

.PHONY: cleanall
cleanall:
	rm -rf .build
