import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from ..models import (
    DBSession,
    Base,
    AdminLevelType,
    HazardType,
    HazardLevel,
    FeedbackStatus,
    )

from .. import load_local_settings


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
    populate_db(engine)


def populate_db(engine):
    DBSession.configure(bind=engine)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with transaction.manager:

        # FeedbackStatus
        for i in [
            (u'TBP', u'To be processed'),
            (u'PIP', u'Process in progress'),  # noqa
            (u'PRD', u'Process done'),
        ]:
            r = FeedbackStatus()
            r.mnemonic, r.title = i
            DBSession.add(r)

        # AdminLevelType
        for i in [
            (u'COU', u'Country', u'Administrative division of level 0'),
            (u'PRO', u'Province', u'Administrative division of level 1'),
            (u'REG', u'Region', u'Administrative division of level 2'),
        ]:
            r = AdminLevelType()
            r.mnemonic, r.title, r.description = i
            DBSession.add(r)

        # HazardLevel
        for i in [
            (u'HIG', u'High', 1),
            (u'MED', u'Medium', 2),
            (u'LOW', u'Low', 3),
            (u'NPR', u'Not previously reported', 4),  # noqa
        ]:
            r = HazardLevel()
            r.mnemonic, r.title, r.order = i
            DBSession.add(r)

        # HazardType
        for i in [
            (u'FL', u'Flood', 1),
            (u'EQ', u'Earthquake', 2),
            (u'DG', u'Drought', 3),
            (u'VA', u'Volcanic ash', 7),
            (u'CY', u'Cyclone', 4),
            (u'TS', u'Tsunami', 6),
            (u'SS', u'Storm surge', 5),
            (u'LS', u'Landslide', 8),
        ]:
            r = HazardType()
            r.mnemonic, r.title, r.order = i
            DBSession.add(r)

    DBSession.remove()
