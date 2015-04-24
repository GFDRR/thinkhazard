Database
========

Data model
----------

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
```

Step 2: load the administrative data

```shell
$ psql -d thinkhazard
thinkhazard=# COPY datamart.administrativedivision FROM '/var/sig/adm-div_20150420.csv' WITH DELIMITER ',' ENCODING 'utf-8';
```

Step3: populate the admin division/hazard category relation table

```shell
$ psql -d thinkhazard
thinkhazard=# COPY datamart.rel_hazardcategory_administrativedivision FROM '/var/sig/poc-morocco-EQ_rel-hazardcategory-administrativedivision.csv' WITH DELIMITER ',' ENCODING 'utf-8';
```

