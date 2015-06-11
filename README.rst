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
