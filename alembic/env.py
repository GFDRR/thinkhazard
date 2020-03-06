"""Pylons bootstrap environment.

Place 'pylons_config_file' into alembic.ini, and the application will
be loaded from there.

"""
import os

from alembic import context
from pyramid.scripts.common import parse_vars, get_config_loader

from thinkhazard.session import get_engine

config = context.config
app = context.config.get_main_option("type")
loader = get_config_loader("{}#{}".format(os.environ['INI_FILE'], app))
loader.setup_logging()
settings = loader.get_wsgi_app_settings()
engine = get_engine(settings)

# add your model's MetaData object here
# for 'autogenerate' support
from thinkhazard import models  # noqa
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
        print('=> ignore table: %s' % name)
        return False
    if type_ == "index" and name in exclude_indexes:
        print('=> ignore index: %s' % name)
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
    context.configure(
        url=engine.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    with engine.connect() as connection:  # noqa
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations(engine_name=app)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
