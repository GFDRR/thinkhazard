import unittest
import os
import ConfigParser

from paste.deploy import loadapp

from ..models import (
    Base,
    DBSession,
    )

local_settings_path = 'local.tests.ini'

# raise an error if the file doesn't exist
with open(local_settings_path):
    pass

def populate_db():
    config = ConfigParser.ConfigParser()
    config.read(local_settings_path)
    db_url = config.get('app:main', 'sqlalchemy.url')

    from sqlalchemy import create_engine
    engine = create_engine(db_url)

    from ..scripts.initializedb import populate_db as populate
    populate(engine)

populate_db()


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        from .. import main
        from webtest import TestApp

        conf_dir = os.getcwd()
        config = 'config:tests.ini'

        app = loadapp(config, relative_to=conf_dir)
        self.testapp = TestApp(app)

    def tearDown(self):
        del self.testapp
