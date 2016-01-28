import unittest
import os
import transaction

from paste.deploy import loadapp

from ...models import (
    DBSession,
    AdministrativeDivision,
    ClimateChangeRecommendation,
    FurtherResource,
    HazardCategory,
    HazardCategoryAdministrativeDivisionAssociation,
    HazardCategoryFurtherResourceAssociation,
    HazardCategoryTechnicalRecommendationAssociation,
    HazardLevel,
    HazardSet,
    HazardType,
    Layer,
    Output,
    TechnicalRecommendation,
    )

from shapely.geometry import (
    MultiPolygon,
    Polygon,
    )
from geoalchemy2.shape import from_shape


def populate_db():
    DBSession.query(Output).delete()
    DBSession.query(Layer).delete()
    DBSession.query(HazardSet).delete()

    DBSession.query(HazardCategoryFurtherResourceAssociation).delete()
    DBSession.query(FurtherResource).delete()
    DBSession.query(HazardCategoryTechnicalRecommendationAssociation).delete()
    DBSession.query(ClimateChangeRecommendation).delete()
    DBSession.query(HazardCategoryAdministrativeDivisionAssociation).delete()
    DBSession.query(HazardCategory).delete()
    DBSession.query(AdministrativeDivision).delete()

    shape = MultiPolygon([
        Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    ])
    geometry = from_shape(shape, 4326)

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

    shape = MultiPolygon([
        Polygon([(0, 0), (0, 1), (.5, 1), (.5, 0), (0, 0)])
    ])
    geometry = from_shape(shape, 4326)

    div_level_3_1 = AdministrativeDivision(**{
        'code': 30,
        'leveltype_id': 3,
        'name': u'Division level 3 - 1'
    })
    div_level_3_1.parent_code = div_level_2.code
    div_level_3_1.geom = geometry
    div_level_3_1.hazardcategories = []

    shape = MultiPolygon([
        Polygon([(.5, 0), (.5, 1), (1, 1), (1, 0), (.5, 0)])
    ])
    geometry = from_shape(shape, 4326)

    div_level_3_2 = AdministrativeDivision(**{
        'code': 31,
        'leveltype_id': 3,
        'name': u'Division level 3 - 2'
    })
    div_level_3_2.parent_code = div_level_2.code
    div_level_3_2.geom = geometry
    div_level_3_2.hazardcategories = []

    category_eq_hig = HazardCategory(**{
        'general_recommendation': u'General recommendation for EQ HIG',
    })
    category_eq_hig.hazardtype = DBSession.query(HazardType) \
        .filter(HazardType.mnemonic == u'EQ').one()
    category_eq_hig.hazardlevel = DBSession.query(HazardLevel) \
        .filter(HazardLevel.mnemonic == u'HIG').one()

    div_level_3_1.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(**{
            'hazardcategory': category_eq_hig
        })
    )
    div_level_3_2.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(**{
            'hazardcategory': category_eq_hig
        })
    )

    climate_rec = ClimateChangeRecommendation()
    climate_rec.text = u'Climate change recommendation'
    climate_rec.administrativedivision = div_level_1
    climate_rec.hazardtype = DBSession.query(HazardType) \
        .filter(HazardType.mnemonic == u'EQ').one()
    DBSession.add(climate_rec)

    technical_rec = TechnicalRecommendation(**{
        'text': u'Recommendation #1 for earthquake, applied to'
                ' hazard categories HIG, MED and LOW'
    })
    association = HazardCategoryTechnicalRecommendationAssociation(order=1)
    association.hazardcategory = category_eq_hig
    technical_rec.hazardcategory_associations.append(association)
    DBSession.add(technical_rec)

    technical_rec = TechnicalRecommendation(**{
        'text': u'Educational web resources on earthquakes and'
                ' seismic hazard'
    })
    association = HazardCategoryTechnicalRecommendationAssociation(order=1)
    association.hazardcategory = category_eq_hig
    technical_rec.hazardcategory_associations.append(association)
    DBSession.add(technical_rec)

    category_fl_med = HazardCategory(**{
        'general_recommendation': u'General recommendation for FL MED',
    })
    category_fl_med.hazardtype = DBSession.query(HazardType) \
        .filter(HazardType.mnemonic == u'FL').one()
    category_fl_med.hazardlevel = DBSession.query(HazardLevel) \
        .filter(HazardLevel.mnemonic == u'MED').one()

    div_level_3_1.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(**{
            'hazardcategory': category_fl_med
        })
    )
    DBSession.add(div_level_3_1)
    div_level_3_2.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(**{
            'hazardcategory': category_fl_med
        })
    )
    DBSession.add(div_level_3_2)

    further_resource = FurtherResource(**{
        'text': u'Educational web resources on earthquakes and' +
                ' seismic hazard',
        'url': u'http://earthquake.usgs.gov/learn/?source=sitemap'
    })
    association = HazardCategoryFurtherResourceAssociation(order=1)
    association.hazardcategory = category_eq_hig
    further_resource.hazardcategory_associations.append(association)
    DBSession.add(further_resource)

    # Add further resource for one division only
    further_resource = FurtherResource(**{
        'text': u'Further resource specific to division level 3 - 2',
        'url': u'http://domain.com/the/document/url.txt'
    })
    association = HazardCategoryFurtherResourceAssociation(order=2)
    association.hazardcategory = category_eq_hig
    association.administrativedivision = div_level_3_2
    further_resource.hazardcategory_associations.append(association)
    DBSession.add(further_resource)

    transaction.commit()


class BaseTestCase(unittest.TestCase):

    def setUp(self):  # NOQA
        populate_db()

        from webtest import TestApp

        conf_dir = os.getcwd()
        config = 'config:tests.ini'

        app = loadapp(config, relative_to=conf_dir)
        self.testapp = TestApp(app)

    def tearDown(self):  # NOQA
        del self.testapp
