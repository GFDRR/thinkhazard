# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 by the GFDRR / World Bank
#
# This file is part of ThinkHazard.
#
# ThinkHazard is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# ThinkHazard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# ThinkHazard.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

from sqlalchemy import engine_from_config
from pyramid.paster import setup_logging
from pyramid.scripts.common import parse_vars
from alembic.config import Config
from alembic import command

from ..settings import load_full_settings
from ..models import (
    Base,
    DBSession,
    AdminLevelType,
    HazardCategory,
    HazardLevel,
    HazardType,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print(('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd)))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = load_full_settings(config_uri, options=options)

    engine = engine_from_config(settings, 'sqlalchemy.')
    with engine.begin() as connection:
        initdb(connection, drop_all='--force' in options)

    # generate the Alembic version table and stamp it with the latest revision
    alembic_cfg = Config('alembic.ini')
    alembic_cfg.set_section_option(
        'alembic', 'sqlalchemy.url', engine.url.__str__())
    command.stamp(alembic_cfg, 'head')


def initdb(connection, drop_all=False):
    if drop_all:
        if schema_exists(connection, 'processing'):
            connection.execute("DROP SCHEMA processing CASCADE;")
        if schema_exists(connection, 'datamart'):
            connection.execute("DROP SCHEMA datamart CASCADE;")

    if not schema_exists(connection, 'datamart'):
        connection.execute("CREATE SCHEMA datamart;")

    if not schema_exists(connection, 'processing'):
        connection.execute("CREATE SCHEMA processing;")

    Base.metadata.create_all(connection)

    DBSession.configure(bind=connection)
    populate_datamart()
    DBSession.flush()


def schema_exists(connection, schema_name):
    sql = '''
SELECT count(*) AS count
FROM information_schema.schemata
WHERE schema_name = '{}';
'''.format(schema_name)
    result = connection.execute(sql)
    row = result.first()
    return row[0] == 1


def populate_datamart():
    # AdminLevelType
    for i in [
        ('COU', 'Country', 'Administrative division of level 0'),
        ('PRO', 'Province', 'Administrative division of level 1'),
        ('REG', 'Region', 'Administrative division of level 2'),
    ]:
        r = AdminLevelType()
        r.mnemonic, r.title, r.description = i
        DBSession.add(r)

    # HazardLevel
    for i in [
        ('HIG', 'High', 1),
        ('MED', 'Medium', 2),
        ('LOW', 'Low', 3),
        ('VLO', 'Very low', 4),
    ]:
        r = HazardLevel()
        r.mnemonic, r.title, r.order = i
        DBSession.add(r)

    # HazardType
    for i in [
        ('FL', 'River flood', 1),
        ('UF', 'Urban flood', 2),
        ('CF', 'Coastal flood', 3),
        ('EQ', 'Earthquake', 4),
        ('LS', 'Landslide', 5),
        ('TS', 'Tsunami', 6),
        ('VA', 'Volcano', 7),
        ('CY', 'Cyclone', 8),
        ('DG', 'Water scarcity', 9),
        ('EH', 'Extreme heat', 10),
        ('WF', 'Wildfire', 11),
        ('AP', 'Air pollution', 12),
    ]:
        r = HazardType()
        r.mnemonic, r.title, r.order = i
        DBSession.add(r)

    # HazardCategory
    hazardlevels = DBSession.query(HazardLevel)
    for hazardtype in DBSession.query(HazardType):
        for hazardlevel in hazardlevels:
            r = HazardCategory()
            r.hazardtype = hazardtype
            r.hazardlevel = hazardlevel
            r.general_recommendation = 'General recommendation for {} {}'\
                .format(hazardtype.mnemonic, hazardlevel.mnemonic)
            DBSession.add(r)
