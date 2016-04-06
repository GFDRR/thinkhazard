from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import logging
from sqlalchemy.exc import OperationalError
from thinkhazard.settings import load_local_settings
from thinkhazard import models

USE_TWOPHASE = False

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# MetaData object for 'autogenerate' support
target_metadata = models.Base.metadata


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
    """Ignore the indices and table specified in the ini file.
    """
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
    autogenerating = context.config.cmd_opts and \
                     'autogenerate' in context.config.cmd_opts and \
                     context.config.cmd_opts.autogenerate
    if autogenerating:
        # when generating migration scripts only check the 'admin' db
        names = ['admin']
    else:
        names = ['public', 'admin']

    # for the direct-to-DB use case, start a transaction on all
    # engines, then run all migrations, then commit all transactions.
    engines = {}
    for name in names:
        settings = context.config.get_section('app:{}'.format(name))
        settings.update(config.get_section(config.config_ini_section))
        load_local_settings(settings, name)
        engine = engine_from_config(
            settings,
            prefix='sqlalchemy.',
            poolclass=pool.NullPool)

        try:
            connection = engine.connect()
        except OperationalError as exc:
            if name == 'public':
                # if the 'public' database was not created yet, skip
                logger.warning(
                    'failed to connect to public database (skipping): '
                    '{}'.format(exc))
                continue
            else:
                raise exc

        engines[name] = {
            'engine': engine,
            'connection': connection,
            'transaction': connection.begin_twophase() if USE_TWOPHASE
            else connection.begin()
        }

    try:
        for name, rec in engines.items():
            logger.info("Migrating database %s" % name)
            context.configure(
                connection=rec['connection'],
                upgrade_token="upgrades",
                downgrade_token="downgrades",
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
