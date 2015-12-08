import os
import sys

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from ..models import Base  # NOQA

from .. import load_local_settings

from thinkhazard_common.scripts.initializedb import initdb


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)

    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    with engine.begin() as db:
        populate_db(db)


def populate_db(engine, drop_all=False):
    initdb(engine, drop_all=drop_all)
