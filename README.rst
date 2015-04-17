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
* `mapnik-utils`, `libmapnik2.2`, `libmapnik-dev`, `python-mapnik`

Getting Started
===============

Create a Python virtual environment and install the project into it::

    $ make install

Run the development server::

    $ make serve

Now point your browser to http://localhost:6543
