import unittest
import os
import ConfigParser
import transaction

from paste.deploy import loadapp

from ..models import (
    Base,
    DBSession,
    AdministrativeDivision,
    )

from shapely.geometry import (
    MultiPolygon,
    Polygon,
    )
from geoalchemy2.shape import from_shape

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

    with transaction.manager:

        div_level_0 = AdministrativeDivision(**{
            'code': 10,
            'leveltype_id': 1,
            'name': u'Division level 1'
        })
        DBSession.add(div_level_0)

        div_level_1 = AdministrativeDivision(**{
            'code': 20,
            'leveltype_id': 2,
            'name': u'Division level 2'
        })
        div_level_1.parent_code = div_level_0.code
        DBSession.add(div_level_1)

        div_level_2 = AdministrativeDivision(**{
            'code': 30,
            'leveltype_id': 3,
            'name': u'Division level 3'
        })
        div_level_2.parent_code = div_level_1.code
        shape = MultiPolygon([
            Polygon([(7.23, 41.25), (7.23, 41.12), (7.41, 41.20)])])
        geometry = from_shape(shape, 3857)
        div_level_2.geom = geometry
        DBSession.add(div_level_2)

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
