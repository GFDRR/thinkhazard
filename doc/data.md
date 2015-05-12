Data
====

Raster
------

The maps displayed in report pages uses [NaturalEarth](http://www.naturalearthdata.com/) as their background layers. More specifically, the "Natural Earth II with Shaded Relief, Water, and Drainages" layer is used, in "medium size". Download the zip file from http://www.naturalearthdata.com/downloads/10m-raster-data/10m-natural-earth-2/.  The name of the zip is `NE2_LR_LC_SR_W_DR.zip`.

Unzip the downloaded zip file in the `data` directory of the project. If you want to place it elsewhere you will need to adjust the `rasterfile` variable in the `development.ini` file. Note that `production.ini` assumes that the tif is located at `/var/sig/NE2_LR_LC_SR_W_DR/NE2_LR_LC_SR_W_DR.tif`, `/var/sig` being the directory where all the geo data is stored on the project's server.

Database schema
---------------

First, a database named `thinkhazard` and a schema named `datamart` should be
created:

```shell
$ createdb thinkhazard
$ psql -d thinkhazard -c 'CREATE EXTENSION postgis;'
$ psql -d thinkhazard -c 'CREATE SCHEMA datamart;'
$ psql -d thinkhazard -c 'GRANT ALL ON SCHEMA datamart TO "www-data";'
```

The database tables can then be created using the `initialize_thinkhazard_db`
console script:

```shell
$ .build/venv/bin/initialize_thinkhazard_db production.ini
```

Database data
-------------

The BRGM team is currently responsible for the database data (a.k.a. the
``datamart``). They provide a SQL script that populates the database. This
script is ``/var/sig/thor-data-backup_20150512_v2.backup`` on the demo server.

First of all, edit this script and check that the path to the
``adm-div_20150505.csv`` file is correct. It should be
``/var/sig/adm-div_20150505.csv``.

Then run the following command as the ``postgres`` user:

```shell
$ psql -d thinkhazard -f /var/sig/thor-data-backup_20150512_v2.backup
```
