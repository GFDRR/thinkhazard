import unittest
import os
import ConfigParser
import transaction

from paste.deploy import loadapp

from ..models import (
    DBSession,
    AdministrativeDivision,
    HazardCategory,
    HazardType,
    HazardLevel,
    ClimateChangeRecommendation,
    #AdditionalInformation,
    #AdditionalInformationType,
    #HazardCategoryAdditionalInformationAssociation,
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

        category_eq_hig = HazardCategory(**{
            'general_recommendation': u'General recommendation for EQ HIG',
        })
        category_eq_hig.hazardtype = DBSession.query(HazardType) \
            .filter(HazardType.mnemonic == u'EQ').one()
        category_eq_hig.hazardlevel = DBSession.query(HazardLevel) \
            .filter(HazardLevel.mnemonic == u'HIG').one()
        div_level_3.hazardcategories.append(category_eq_hig)

        climate_rec = ClimateChangeRecommendation()
        climate_rec.text = u'Climate change recommendation'
        climate_rec.administrativedivision = div_level_3
        climate_rec.hazardtype =  DBSession.query(HazardType) \
            .filter(HazardType.mnemonic == u'EQ').one()
        DBSession.add(climate_rec)

        #info = AdditionalInformation(**{
            #'mnemonic': u'REC1_EQ',
            #'title': u'Recommendation #1 for earthquake, applied to hazard'
                     #'categories HIG, MED and LOW',
            #'description': u'Recommendation #1 for earthquake, applied to'
                           #' hazard categories HIG, MED and LOW'
        #})
        #info.type = DBSession.query(AdditionalInformationType) \
            #.filter(AdditionalInformationType.mnemonic == u'REC').one()
        #association = HazardCategoryAdditionalInformationAssociation(order=1)
        #association.hazardcategory = category_eq_hig
        #info.hazardcategory_associations.append(association)
        #DBSession.add(info)

        #info = AdditionalInformation(**{
            #'mnemonic': u'AVD1_EQ',
            #'title': u'Educational web resources on earthquakes and seismic'
                     #' hazard',
            #'description': u'Educational web resources on earthquakes and'
                           #' seismic hazard'
        #})
        #info.type = DBSession.query(AdditionalInformationType) \
            #.filter(AdditionalInformationType.mnemonic == u'AVD').one()
        #association = HazardCategoryAdditionalInformationAssociation(order=1)
        #association.hazardcategory = category_eq_hig
        #info.hazardcategory_associations.append(association)
        #DBSession.add(info)

        category_fl_med = HazardCategory(**{
            'general_recommendation': u'General recommendation for FL MED',
        })
        category_fl_med.hazardtype = DBSession.query(HazardType) \
            .filter(HazardType.mnemonic == u'FL').one()
        category_fl_med.hazardlevel = DBSession.query(HazardLevel) \
            .filter(HazardLevel.mnemonic == u'MED').one()
        div_level_3.hazardcategories.append(category_fl_med)
        DBSession.add(div_level_3)

populate_db()


class BaseTestCase(unittest.TestCase):

    def setUp(self):  # NOQA
        from webtest import TestApp

        conf_dir = os.getcwd()
        config = 'config:tests.ini'

        app = loadapp(config, relative_to=conf_dir)
        self.testapp = TestApp(app)

    def tearDown(self):  # NOQA
        del self.testapp
