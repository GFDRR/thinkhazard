ThinkHazard
###########


.. image:: https://api.travis-ci.org/GFDRR/thinkhazard.svg?branch=master
    :target: https://travis-ci.org/GFDRR/thinkhazard
    :alt: Travis CI Status

System-level dependencies
=========================

The following packages must be installed on the system:

* `libpq-dev`
* `node`/`npm`
* `gcc`
* `python-devel`
* `python-virtualenv`
* `apache2`

Getting Started
===============

Create a Python virtual environment and install the project into it::

    $ make install

Build CSS files (from less files)::

    $ make build

Run the development server::

    $ make serve

Now point your browser to http://localhost:6543.

Use Apache ``mod_wsgi``
=======================

The ``mod_wsgi`` Apache module is used on the demo server. Using ``mod_wsgi``
requires some Apache configuration and a WSGI application script file.

These files can be created with the ``modwsgi`` target::

    $ make modwsgi

This command creates ``.build/apache.conf``, the Apache configuration file to
include in the main Apache configuration file, and
``.build/venv/thinkhazard.wsgi``, the WSGI application script file.

By default, the application location is ``/main/wsgi``. To change the location
you can set ``INSTANCEID`` on the ``make modwsgi`` command line. For example::

    $ make modwsgi INSTANCEID=elemoine

With this the application location will be ``/elemoine/wsgi``.

Use ``local.ini``
=================

The settings defined in the ``[app:main]`` section of ``development.ini`` can
be overriden by creating a ``local.ini`` file at the root of the project.

For example, you can define a specific database connection with a ``local.ini``
file that looks like this::

    [app:main]
    sqlalchemy.url = postgresql://www-data:www-data@localhost:9999/thinkhazard

Deploy on server
================

The demo application is available at
http://wb-thinkhazard.dev.sig.cloud.camptocamp.net/main/wsgi.

To update the demo application use the following::

    $ ssh <demo>
    $ cd /var/www/vhosts/wb-thinkhazard/private/thinkhazard
    $ sudo -u sigdev git fetch origin
    $ sudo -u sigdev git merge --ff-only origin/master
    $ sudo -u sigdev make clean install build modwsgi
    $ sudo apache2ctl configtest
    $ sudo apache2ctl graceful

Run tests
=========

In order to run tests, you'll need to create a separate Database::

    sudo -u postgres createdb -O www-data thinkhazard_tests
    sudo -u postgres psql -d thinkhazard_tests -c "CREATE EXTENSION postgis;"

You'll also have to define the specific settings. For this purpose, you'll have
to create a ``local.tests.ini`` with the following content (to be adapted to
your environnement)::

    [app:main]
    sqlalchemy.url = postgresql://www-data:www-data@localhost/thinkhazard_tests

Then you should be able to run the tests with the following command::

    $ make test
