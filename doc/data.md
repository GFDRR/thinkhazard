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

The recommendations are currently provided as documents (xls or doc files).

In order to be put in the database a script has been developed to import these
recommendations into the database.

Here are the commands to be run:

```shell
.build/venv/bin/import_recommandations
```

See the script in order to get more information.
