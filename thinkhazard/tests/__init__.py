# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 by the GFDRR / World Bank
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

from sqlalchemy import engine_from_config
from pyramid.paster import (
    get_appsettings,
)
from .. import load_local_settings
from ..scripts.initializedb import initdb

local_settings_path = 'local.tests.ini'

# raise an error if the file doesn't exist
with open(local_settings_path):
    pass


def populatedb():
    settings = get_appsettings('development.ini', options={})

    settings['local_settings_path'] = local_settings_path
    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    initdb(engine, True)

populatedb()
