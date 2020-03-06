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

import transaction
from thinkhazard.session import get_engine, get_session_factory, get_tm_session
from thinkhazard.settings import load_full_settings
from thinkhazard.scripts import wait_for_db
from thinkhazard.scripts.initializedb import initdb


settings = load_full_settings("c2c://tests.ini", name="admin")
engine = get_engine(settings)
session_factory = get_session_factory(engine)
DBSession = get_tm_session(session_factory, transaction.manager)


def populatedb():
    wait_for_db(engine)
    with engine.begin() as connection:
        initdb(connection, True)


populatedb()
