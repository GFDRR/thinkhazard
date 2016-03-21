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

Create a database::

    $ sudo -u postgres createdb -O www-data thinkhazard
    $ sudo -u postgres psql -d thinkhazard -c 'CREATE EXTENSION postgis;'

If you want to use a different user or different database name, you'll have to
provide your own configuration file. See "Use local.ini" section
below.

Create the required schema and tables and populate the enumeration tables::

    $ make populatedb

Note: this may take a while.

If you don't want to import all the world administrative divisions, you can
import only a subset::

    $ make populatedb DATA=turkey
    $ make populatedb DATA=indonesia

You're now ready to harvest, download and process the data::

    $ make harvest
    $ make download
    $ make complete
    $ make process
    $ make decisiontree

For more options, see::

    $ make help

Build CSS files (from less files)::

    $ make build

Run the development server::

    $ make serve

Now point your browser to http://localhost:6543.

Configure using thinkhazard_processing.yaml
===========================================

Keys in processing configuration file:


hazard_types
------------

Harvesting and processing configuration for each hazard type.
One entry for each hazard type mnemonic.

Possible subkeys include the following:

- ``hazard_type``: Corresponding hazard_type value in geonode.

- ``return_periods``: One entry per hazard level mnemonic with
  corresponding return periods. Each return period can be a value or a list
  with minimum and maximum values, example:

  .. code:: yaml

      return_periods:
        HIG: [10, 25]
        MED: 50
        LOW: [100, 1000]

- ``thresholds``: Flexible threshold configuration.

  This can be a simple and global value per hazardtype. Example:

  .. code:: yaml

       thresholds: 1700

  But it can also contain one or many sublevels for complex configurations:

  1) ``global`` and ``local`` entries for corresponding hazardsets.
  2) One entry per hazard level mnemonic.
  3) One entry per hazard unit from geonode.

  Example:

  .. code:: yaml

       thresholds:
         global:
           HIG:
             unit1: value1
             unit2: value2
           MED:
             unit1: value1
             unit2: value2
           LOW:
             unit1: value1
             unit2: value2
         local:
           unit1: value1
           unit2: value2

- ``values``: One entry per hazard level,
  with list of corresponding values in preprocessed layer.
  If present, the layer is considered as preprocessed, and the above
  ``thresholds`` and ``return_periods`` are not taken into account.
  Example:

  .. code:: yaml

      values:
        HIG: [103]
        MED: [102]
        LOW: [101]
        VLO: [100, 0]

Processing tasks
================

Thinkhazard_processing provides several consecutive tasks to populate the
thinkhazard datamart database. These are:

``.build/venv/bin/harvest [--force] [--dry-run]``

Harvest metadata from GeoNode, create HazardSet and Layer records.

``.build/venv/bin/download [--title] [--force] [--dry-run]``

Download raster files in data folder.

``.build/venv/bin/complete [--force] [--dry-run]``

Identify hazardsets whose layers have been fully downloaded, infer several
fields and mark these hazardsets complete.

``.build/venv/bin/process [--hazarset_id ...] [--force] [--dry-run]``

Calculate output from hazardsets and administrative divisions.

``.build/venv/bin/decision_tree [--force] [--dry-run]``

Apply the decision tree followed by upscaling on process outputs to get the final
relations between administrative divisions and hazard categories.

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

Configure admin username/password
---------------------------------

By default, the admin interface authentification file is
``/var/www/vhosts/wb-thinkhazard/conf/.htpasswd``. To change the location you
can set ``AUTHUSERFILE`` on the ``make modwsgi`` command line.

To create a authentification file ``.htpassword`` with ``admin`` as the initial
user ::

    $ htpasswd -c .htpassword username

It will prompt for the password.

Add or modify ``username2`` in the password file ``.htpassword``::

   $ htpasswd .htpassword username2

Use ``local.ini``
=================

The settings defined in the ``[app:main]`` section of ``development.ini`` can
be overriden by creating a ``local.ini`` file at the root of the project.

For example, you can define a specific database connection with a ``local.ini``
file that looks like this::

    [app:main]
    sqlalchemy.url = postgresql://www-data:www-data@localhost:9999/thinkhazard
    data_path: /path/to/data/folder

``data_path`` is the path to data folder. It will contain the donwloaded raster
files as well as archive to generated PDF reports.
It defaults to ``/tmp``. For production, we recommend you change this location
to a dedicated disk partition.

Analytics
---------

If you want to get some analytics on the website usage (via Google analytics),
you can add the tracking code using a `analytics` variable::

    analytics = UA-75358940-1

Deploy on server
================

The demo application is available at
http://wb-thinkhazard.dev.sig.cloud.camptocamp.net/main/wsgi.

To update the demo application use the following::

    ssh <demo>
    cd /var/www/vhosts/wb-thinkhazard/private/thinkhazard
    sudo -u sigdev git fetch origin
    sudo -u sigdev git merge --ff-only origin/master
    sudo -u sigdev make clean install build modwsgi
    sudo apache2ctl configtest
    sudo apache2ctl graceful

Run tests
=========

In order to run tests, you'll need to create a separate Database::

    sudo -u postgres createdb -O www-data thinkhazard_tests
    sudo -u postgres psql -d thinkhazard_tests -c 'CREATE EXTENSION postgis;'

You'll also have to define the specific settings. For this purpose, you'll have
to create a ``local.tests.ini`` with the following content (to be adapted to
your environnement)::

    [app:main]
    sqlalchemy.url = postgresql://www-data:www-data@localhost/thinkhazard_tests

Then you should be able to run the tests with the following command::

    $ make test

Feedback
========

The ``feedback_form_url`` can be configured in the ``local.ini`` file.
