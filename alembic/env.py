from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import ConfigParser
import re
import os
from thinkhazard.settings import load_local_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from thinkhazard import models
target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def exclude_data_from_config(name, section=None):
    section = section or 'alembic:exclude'
    _sec_data = config.get_section(section)
    if not _sec_data:
        return []
    _data = _sec_data.get(name, None)
    return [d.strip() for d in _data.split(",")] if _data is not None else []

exclude_tables = exclude_data_from_config('tables')
exclude_indexes = exclude_data_from_config('indexes')

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in exclude_tables:
        print '=> ignore table: %s' % name
        return False
    if type_ == "index" and name in exclude_indexes:
        print '=> ignore index: %s' % name
        return False
    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    settings = config.get_section(config.config_ini_section)
    load_local_settings(settings)
    connectable = engine_from_config(
        settings,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
