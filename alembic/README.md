Generic single-database configuration.

# Generation of migration scripts

Migration scripts are created each time modifications are made on database model or data.

Do the adequate modifications in the model (`models.py`).

Then autogenerate the migration script.

```
.build/venv/bin/alembic revision --autogenerate
```

Make sure the script looks correct. Adjust if necesary. Run the migration (see below) and make sure the database is updated correctly.

Commit the changes.

# Run a migration

A migration should be run each time the application code is updated or if you just created a migration script.

```
.build/venv/bin/alembic upgrade head
```

# More information

Please refer to Alembic documentation for more information.
http://alembic.readthedocs.org/en/latest/
