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

import pytest
import transaction
from pyramid import testing
from pyramid.paster import bootstrap
from webtest import TestApp

from thinkhazard.session import get_engine, get_session_factory, get_tm_session
from thinkhazard.settings import load_full_settings
from thinkhazard.scripts import wait_for_db
from thinkhazard.scripts.initializedb import initdb


@pytest.fixture(scope="session")
def settings():
    return load_full_settings("c2c://tests.ini", name="admin")

@pytest.fixture(scope="session")
def engine(settings):
    return get_engine(settings)

@pytest.fixture(scope="session", autouse=True)
def populatedb():
    wait_for_db(engine)
    with engine.begin() as connection:
        initdb(connection, True)

@pytest.fixture(scope="session")
def dbsession(engine):
    session_factory = get_session_factory(engine)
    return get_tm_session(session_factory, transaction.manager)

@pytest.fixture(scope="class")
def transact(dbsession):
    t = dbsession.begin()
    yield
    t.rollback()

@pytest.fixture
def nested_transact(dbsession):
    t = dbsession.begin_nested()
    yield
    t.rollback()

@pytest.fixture
def public_testapp(dbsession):
    env = bootstrap('c2c://tests.ini#public')
    config = testing.setUp(registry=env["registry"])
    config.add_request_method(lambda request: dbsession, "dbsession", reify=True)
    app = config.make_wsgi_app()
    return TestApp(app)

@pytest.fixture
def admin_testapp(dbsession):
    env = bootstrap('c2c://tests.ini#admin')
    config = testing.setUp(registry=env["registry"])
    config.add_request_method(lambda request: dbsession, "dbsession", reify=True)
    app = config.make_wsgi_app()
    return TestApp(app)
