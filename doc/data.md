Data
====

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
script is ``/var/sig/thor-data-backup_20150512_v3.backup`` on the demo server.

First of all, edit this script and check that the path to the
``adm-div_20150505.csv`` file is correct. It should be
``/var/sig/adm-div_20150505.csv``.

Then run the following command as the ``postgres`` user:

```shell
$ psql -d thinkhazard -f /var/sig/thor_enum_updates_18-06-2015.sql
$ psql -d thinkhazard -f /var/sig/thor_hazard-data_updates_22-06-2015.sql
```
