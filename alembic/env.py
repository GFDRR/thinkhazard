from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import ConfigParser
import logging
import re
import os
from thinkhazard.settings import load_local_settings

USE_TWOPHASE = False

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

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


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # for the direct-to-DB use case, start a transaction on all
    # engines, then run all migrations, then commit all transactions.

    names = ['public', 'admin']
    engines = {}

    for name in names:
        engines[name] = rec = {}
        settings = context.config.get_section('app:{}'.format(name))
        settings.update(config.get_section(config.config_ini_section))
        load_local_settings(settings, name)
        rec['engine'] = engine_from_config(
            settings,
            prefix='sqlalchemy.',
            poolclass=pool.NullPool)

    for name, rec in engines.items():
        engine = rec['engine']
        rec['connection'] = conn = engine.connect()

        if USE_TWOPHASE:
            rec['transaction'] = conn.begin_twophase()
        else:
            rec['transaction'] = conn.begin()

    try:
        for name, rec in engines.items():
            logger.info("Migrating database %s" % name)
            context.configure(
                connection=rec['connection'],
                upgrade_token="%s_upgrades" % name,
                downgrade_token="%s_downgrades" % name,
                target_metadata=target_metadata,
                include_object=include_object,
                include_schemas=True,
            )
            context.run_migrations(engine_name=name)

        if USE_TWOPHASE:
            for rec in engines.values():
                rec['transaction'].prepare()

        for rec in engines.values():
            rec['transaction'].commit()
    except:
        for rec in engines.values():
            rec['transaction'].rollback()
        raise
    finally:
        for rec in engines.values():
            rec['connection'].close()

run_migrations_online()
