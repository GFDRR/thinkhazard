Generic single-database configuration.

# Generation of migration scripts

Migration scripts are created each time modifications are made on the database model or data.

For example if you want to add a new field to a table, add the column in the SQLAlchemy
model (`models.py`).

Then autogenerate the migration script with:

```
.build/venv/bin/alembic revision --autogenerate -m 'Add column x'
```

A new migration script is created in `alembic/versions/`. Make sure the script looks correct, adjust if necessary.

To add the new column to the database(s), run the migration (see below) and make sure the database is updated correctly.

Commit the changes.

# Run a migration

A migration should be run each time the application code is updated or if you just created a migration script.

```
.build/venv/bin/alembic upgrade head
```

# Two-phase commit

To make sure that migrations are correctly applied to both databases or none,
the migration is by default doing a two-phase commit.

Prepared transactions which are required for the two-phase commit
are by default disabled on PostgreSQL. If so you will get an error message like
*'(psycopg2.OperationalError)  prepared transactions are disabled'*.

To enable, set `max_prepared_transactions` in `postgresql.conf`
(the recommend value is `max_connections`, by default `100`). Restart required.

More information here:
http://www.postgresql.org/docs/9.4/static/runtime-config-resource.html

To run the migration without using a two-phase commit, the `twophase` flag can be disabled:

```
.build/venv/bin/alembic -x twophase=False upgrade head
```

# More information

Please refer to Alembic documentation for more information.
http://alembic.readthedocs.org/en/latest/
