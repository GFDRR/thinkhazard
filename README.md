# ThinkHazard

[![Build Status](https://travis-ci.org/GFDRR/thinkhazard.svg?branch=master)](https://travis-ci.org/GFDRR/thinkhazard)

## System-level dependencies

The following packages must be installed on the system:

-   libpq-dev
-   node/npm
-   gcc
-   python-devel
-   python-virtualenv
-   apache2
-   postgis

## Getting Started

The following commands assume that the system is Debian/Ubuntu. Commands may need to be adapted when working on a different system.

Create a Python virtual environment and install the project into it:

    $ make install

Create a database:

    $ sudo -u postgres createdb -O www-data thinkhazard_admin
    $ sudo -u postgres psql -d thinkhazard_admin -c 'CREATE EXTENSION postgis;'
    $ sudo -u postgres psql -d thinkhazard_admin -c 'CREATE EXTENSION unaccent;'

If you want to use a different user or different database name, you’ll have to provide your own configuration file. See “Use local.ini” section below.

Create the required schema and tables and populate the enumeration tables:

    $ make populatedb

Note: this may take a while. If you don’t want to import all the world administrative divisions, you can import only a subset:

    $ make populatedb DATA=turkey

or:

    $ make populatedb DATA=indonesia

You’re now ready to harvest, download and process the data:

    $ make harvest
    $ make download
    $ make complete
    $ make process
    $ make decisiontree

For more options, see:

    $ make help

Run the development server:

    $ make serve_public

for the public site or:

    $ make serve_admin

for the admin interface.

Now point your browser to <http://localhost:6543>.

## Processing tasks

Administrator can also launch the different processing tasks with more options.

`.build/venv/bin/harvest [--force] [--dry-run]`

Harvest metadata from GeoNode, create HazardSet and Layer records.

`.build/venv/bin/download [--title] [--force] [--dry-run]`

Download raster files in data folder.

`.build/venv/bin/complete [--force] [--dry-run]`

Identify hazardsets whose layers have been fully downloaded, infer several fields and mark these hazardsets complete.

`.build/venv/bin/process [--hazardset_id ...] [--force] [--dry-run]`

Calculate output from hazardsets and administrative divisions.

`.build/venv/bin/decision_tree [--force] [--dry-run]`

Apply the decision tree followed by upscaling on process outputs to get the final relations between administrative divisions and hazard categories.

## Publication of admin database on public site

Publication consist in overwriting the public database with the admin one. This can be done using :

`make publish`

And this will execute as follow : \* Lock the public site in maintenance mode. \* Store a publication date in the admin database. \* Backup the admin database in archives folder. \* Create a new fresh public database. \* Restore the admin backup into public database. \* Unlock the public site from maintenance mode.

## Use Apache `mod_wsgi`

The `mod_wsgi` Apache module is used on the demo server. Using `mod_wsgi` requires some Apache configuration and a WSGI application script file.

These files can be created with the `modwsgi` target:

    $ make modwsgi

This command creates `.build/apache.conf`, the Apache configuration file to include in the main Apache configuration file, and `.build/venv/thinkhazard.wsgi`, the WSGI application script file.

By default, the application location is `/main/wsgi`. To change the location you can set `INSTANCEID` on the `make modwsgi` command line. For example:

    $ make modwsgi INSTANCEID=elemoine

With this the application location will be `/elemoine/wsgi`.

### Configure admin username/password

By default, the admin interface authentification file is `/var/www/vhosts/wb-thinkhazard/conf/.htpasswd`. To change the location you can set `AUTHUSERFILE` on the `make modwsgi` command line.

To create a authentification file `.htpasswd` with `admin` as the initial user :

    $ htpasswd -c .htpasswd username

It will prompt for the passwd.

Add or modify `username2` in the password file `.htpasswd`:

    $ htpasswd .htpasswd username2

## Use `local.ini`

The settings defined `development.ini` can be overriden by creating a `local.ini` file at the root of the project.

The following sections are intended to be overriden: `[app:public]` and `[app:admin]`.

The following variables can be configured:

-   `sqlalchemy.url`: URL to the database. It defaults to `postgresql://www-data:www-data@localhost:5432/thinkhazard` for the public app and to `postgresql://www-data:www-data@localhost:5432/thinkhazard_admin` for the admin app.
-   `data_path`: Path to data folder. It’s the location where the raster files will be downloaded. Defaults to `/tmp`.
-   `backup_path`: Path to database backup archives path. Only relevant for the admin app. It defaults to `/srv/archives/backups`.
-   `pdf_archive_path`: Path to PDF report archives path. Only relevant for the public app. It defaults to `/srv/archives/reports`.
-   `feedback_form_url`: URL to the form where the users will be redirected when clicking on the feedback link.
-   `analytics`: Tracking code for the google analytics account. Should be set on the public section only.

Example `local.ini` file:

    [app:public]
    sqlalchemy.url = postgresql://www-data:www-data@localhost/developer
    pdf_archive_path = /home/developer/tmp/reports

    [app:admin]
    sqlalchemy.url = postgresql://www-data:www-data@localhost/developer_admin
    backup_path = /home/developer/tmp/backups

### Analytics

If you want to get some analytics on the website usage (via Google analytics), you can add the tracking code using a analytics variable:

    analytics = UA-75358940-1

## Deploy on server

The demo application is available at <http://wb-thinkhazard.dev.sig.cloud.camptocamp.net/main/wsgi>.

To update the demo application use the following:

    ssh <demo>
    cd /var/www/vhosts/wb-thinkhazard/private/thinkhazard
    sudo -u sigdev git fetch origin
    sudo -u sigdev git merge --ff-only origin/master
    sudo -u sigdev make clean install modwsgi
    sudo apache2ctl configtest
    sudo apache2ctl graceful

### Run tests

In order to run tests, you’ll need to create a separate Database:

    sudo -u postgres createdb -O www-data thinkhazard_tests
    sudo -u postgres psql -d thinkhazard_tests -c 'CREATE EXTENSION postgis;'
    sudo -u postgres psql -d thinkhazard_tests -c 'CREATE EXTENSION unaccent;'

You’ll also have to define the specific settings. For this purpose, you’ll have to create a `local.tests.ini` with the following content (to be adapted to your environnement):

    [app:public]
    sqlalchemy.url = postgresql://www-data:www-data@localhost:5432/thinkhazard_tests

    [app:admin]
    sqlalchemy.url = postgresql://www-data:www-data@localhost:5432/thinkhazard_tests

Then you should be able to run the tests with the following command:

    $ make test

### Feedback

The `feedback_form_url` can be configured in the `local.ini` file.

### Configuration of processing parameters

The configuration of the threshold, return periods and units for the different hazard types can be done via the thinkhazard\_processing.yaml.

After any modification to this file, next harvesting will delete all layers, hazardsets and processing outputs. This means that next processing task will have to treat all hazardsets and may take a while (close to one hour).

## hazard\_types

Harvesting and processing configuration for each hazard type. One entry for each hazard type mnemonic.

Possible subkeys include the following:

-   `hazard_type`: Corresponding hazard\_type value in geonode.
-   `return_periods`: One entry per hazard level mnemonic with corresponding return periods. Each return period can be a value or a list with minimum and maximum values, example:

    ```yaml
    return_periods:
      HIG: [10, 25]
      MED: 50
      LOW: [100, 1000]
    ```

-   `thresholds`: Flexible threshold configuration.

    This can be a simple and global value per hazardtype. Example:

    ```yaml
    thresholds: 1700
    ```

    But it can also contain one or many sublevels for complex configurations:

    1.  `global` and `local` entries for corresponding hazardsets.
    2.  One entry per hazard level mnemonic.
    3.  One entry per hazard unit from geonode.

    Example:

    ```yaml
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
        MASK:
          unit1: value1
          unit2: value2
      local:
        unit1: value1
        unit2: value2
    ```

-   `values`: One entry per hazard level, with list of corresponding values in preprocessed layer. If present, the layer is considered as preprocessed, and the above `thresholds` and `return_periods` are not taken into account. Example:

    ```yaml
    values:
      HIG: [103]
      MED: [102]
      LOW: [101]
      VLO: [100, 0]
    ```
