import unittest
import os
import ConfigParser
import transaction

from paste.deploy import loadapp

from ..models import (
    Base,
    DBSession,
    AdministrativeDivision,
    HazardCategory,
    HazardType,
    CategoryType,
    IntensityThreshold,
    TermStatus,
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

        shape = MultiPolygon([
            Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
        ])
        geometry = from_shape(shape, 3857)

        div_level_1 = AdministrativeDivision(**{
            'code': 10,
            'leveltype_id': 1,
            'name': u'Division level 1'
        })
        div_level_1.geom = geometry
        DBSession.add(div_level_1)

        div_level_2 = AdministrativeDivision(**{
            'code': 20,
            'leveltype_id': 2,
            'name': u'Division level 2'
        })
        div_level_2.parent_code = div_level_1.code
        div_level_2.geom = geometry
        DBSession.add(div_level_2)

        div_level_3 = AdministrativeDivision(**{
            'code': 30,
            'leveltype_id': 3,
            'name': u'Division level 3'
        })
        div_level_3.parent_code = div_level_2.code
        div_level_3.geom = geometry
        div_level_3.hazardcategories = []

        category = HazardCategory(**{
            'description': u'Earthquake high threshold 1',
        })
        category.hazardtype = DBSession.query(HazardType) \
            .filter(HazardType.mnemonic == u'EQ').one()
        category.intensitythreshold = DBSession.query(IntensityThreshold) \
            .filter(IntensityThreshold.mnemonic == u'EQ_IT_1').one()
        category.categorytype = DBSession.query(CategoryType) \
            .filter(CategoryType.mnemonic == u'HIG').one()
        category.status = DBSession.query(TermStatus) \
            .filter(TermStatus.mnemonic == u'VAL').one()
        DBSession.add(category)
        div_level_3.hazardcategories.append(category)
        category = HazardCategory(**{
            'description': u'Flood med threshold 1',
        })
        category.hazardtype = DBSession.query(HazardType) \
            .filter(HazardType.mnemonic == u'FL').one()
        category.intensitythreshold = DBSession.query(IntensityThreshold) \
            .filter(IntensityThreshold.mnemonic == u'FL_IT_1').one()
        category.categorytype = DBSession.query(CategoryType) \
            .filter(CategoryType.mnemonic == u'MED').one()
        category.status = DBSession.query(TermStatus) \
            .filter(TermStatus.mnemonic == u'VAL').one()
        DBSession.add(category)
        div_level_3.hazardcategories.append(category)
        DBSession.add(div_level_3)

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
