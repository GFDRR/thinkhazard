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

import unittest
import os
import transaction
from datetime import datetime

from paste.deploy import loadapp

from ...models import (
    DBSession,
    AdministrativeDivision,
    ClimateChangeRecommendation,
    ClimateChangeRecAdministrativeDivisionAssociation as CcrAd,
    FurtherResource,
    Region,
    RegionAdministrativeDivisionAssociation,
    HazardCategory,
    HazardCategoryAdministrativeDivisionAssociation,
    HazardTypeFurtherResourceAssociation,
    HazardCategoryTechnicalRecommendationAssociation,
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

    DBSession.query(HazardTypeFurtherResourceAssociation).delete()
    DBSession.query(FurtherResource).delete()
    DBSession.query(HazardCategoryTechnicalRecommendationAssociation).delete()
    DBSession.query(TechnicalRecommendation).delete()
    DBSession.query(ClimateChangeRecommendation).delete()
    DBSession.query(HazardCategoryAdministrativeDivisionAssociation).delete()
    DBSession.query(RegionAdministrativeDivisionAssociation).delete()
    DBSession.query(AdministrativeDivision).delete()

    DBSession.query(Region).delete()

    hazardtype_eq = DBSession.query(HazardType) \
        .filter(HazardType.mnemonic == u'EQ').one()
    hazardset1 = HazardSet()
    hazardset1.id = u'hazardset1'
    hazardset1.hazardtype = hazardtype_eq
    hazardset1.data_lastupdated_date = datetime.now()
    hazardset1.metadata_lastupdated_date = datetime.now()
    hazardset1.distribution_url = u'http://domain.com/path/'
    hazardset1.owner_organization = u'data_provider'
    DBSession.add(hazardset1)

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

    div_level_1_2 = AdministrativeDivision(**{
        'code': 11,
        'leveltype_id': 1,
        'name': u'Division level 1 2'
    })
    div_level_1_2.geom = geometry
    DBSession.add(div_level_1_2)

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
        'code': 31,
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
        'code': 32,
        'leveltype_id': 3,
        'name': u'Division level 3 - 2'
    })
    div_level_3_2.parent_code = div_level_2.code
    div_level_3_2.geom = geometry
    div_level_3_2.hazardcategories = []

    global_region = Region(**{
        'id': 1,
        'level': 0,
        'name': u'Global region'
    })

    country_region = Region(**{
        'id': 2,
        'level': 3,
        'name': u'Country 1'
    })

    country_region_2 = Region(**{
        'id': 3,
        'level': 3,
        'name': u'Country 2'
    })

    association = RegionAdministrativeDivisionAssociation()
    association.administrativedivision = div_level_1
    global_region.administrativedivisions.append(association)

    association = RegionAdministrativeDivisionAssociation()
    association.administrativedivision = div_level_1
    country_region.administrativedivisions.append(association)

    association = RegionAdministrativeDivisionAssociation()
    association.administrativedivision = div_level_1_2
    country_region_2.administrativedivisions.append(association)

    category_eq_hig = HazardCategory.get('EQ', 'HIG')
    category_eq_hig.general_recommendation = \
        u'General recommendation for EQ HIG'

    association = HazardCategoryAdministrativeDivisionAssociation(**{
        'hazardcategory': category_eq_hig
    })
    association.hazardsets.append(hazardset1)
    div_level_3_1.hazardcategories.append(association)
    div_level_3_2.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(**{
            'hazardcategory': category_eq_hig
        })
    )

    climate_rec = ClimateChangeRecommendation(
        text=u'Climate change recommendation',
        hazardtype=HazardType.get(u'EQ'))
    climate_rec.associations.append(CcrAd(
        administrativedivision=div_level_1,
        hazardtype=HazardType.get(u'EQ')))
    DBSession.add(climate_rec)

    climate_rec = ClimateChangeRecommendation(
        text=u'Climate change recommendation 2',
        hazardtype=HazardType.get(u'EQ'))
    climate_rec.associations.append(CcrAd(
        administrativedivision=div_level_1_2,
        hazardtype=HazardType.get(u'EQ')))
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

    category_fl_med = HazardCategory.get('FL', 'MED')
    category_fl_med.general_recommendation = \
        u'General recommendation for FL MED'

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
        'id': 3
    })
    association = HazardTypeFurtherResourceAssociation()
    association.hazardtype = hazardtype_eq
    association.region = global_region
    further_resource.hazardtype_associations.append(association)
    DBSession.add(further_resource)

    further_resource = FurtherResource(**{
        'text': u'Further resource for earthquake for country 1',
        'id': 5
    })
    association = HazardTypeFurtherResourceAssociation()
    association.hazardtype = hazardtype_eq
    association.region = country_region
    further_resource.hazardtype_associations.append(association)
    DBSession.add(further_resource)

    further_resource = FurtherResource(**{
        'text': u'Further resource for earthquake for country 2',
        'id': 6
    })
    association = HazardTypeFurtherResourceAssociation()
    association.hazardtype = hazardtype_eq
    association.region = country_region_2
    further_resource.hazardtype_associations.append(association)
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
