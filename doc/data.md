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

Populating the database with the data created by the BRGM team for the « POC » requires three steps:

Step 1: load the hazard data

```shell
$ psql -d thinkhazard -f /var/sig/thor_data_updates_23-04-2015_EQ.sql
$ psql -d thinkhazard -f /var/sig/thor_enum_updates_05-05-2015.sql
```

Step 2: load the administrative data

```shell
$ psql -d thinkhazard
thinkhazard=# COPY datamart.administrativedivision FROM '/var/sig/adm-div_20150420.csv' WITH DELIMITER ',' ENCODING 'utf-8';
```

Step3: populate the admin division/hazard category relation table

For the earthquake data:

```shell
$ psql -d thinkhazard
thinkhazard=# COPY datamart.rel_hazardcategory_administrativedivision FROM '/var/sig/poc-morocco-EQ_rel-hazardcategory-administrativedivision.csv' WITH DELIMITER ',' ENCODING 'utf-8';
thinkhazard=# setval('datamart.rel_hazardcategory_administrativedivision_id_seq', 64);
```

For the flood data:

```shell
$ psql -d thinkhazard -f /var/sig/thor_data_updates_24-04-2015_FL.sql
```

