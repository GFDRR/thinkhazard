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

# More information

Please refer to Alembic documentation for more information.
http://alembic.readthedocs.org/en/latest/
