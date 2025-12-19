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


from datetime import datetime

import pytest

from thinkhazard.models import (
    AdministrativeDivision,
    ClimateChangeRecommendation,
    ClimateChangeRecAdministrativeDivisionAssociation as CcrAd,
    FurtherResource,
    Region,
    HazardCategory,
    HazardCategoryAdministrativeDivisionAssociation,
    HazardTypeFurtherResourceAssociation,
    HazardCategoryTechnicalRecommendationAssociation,
    HazardSet,
    HazardType,
    Layer,
    Output,
    TechnicalRecommendation,
    Publication,
    Contact,
    ContactAdministrativeDivisionHazardTypeAssociation as CAdHt,
)

from shapely.geometry import MultiPolygon, Polygon
from geoalchemy2.shape import from_shape


@pytest.fixture(scope="class")
def populate(dbsession, transact):
    dbsession.query(Output).delete()
    dbsession.query(Layer).delete()
    dbsession.query(HazardSet).delete()

    dbsession.query(HazardTypeFurtherResourceAssociation).delete()
    dbsession.query(FurtherResource).delete()
    dbsession.query(HazardCategoryTechnicalRecommendationAssociation).delete()
    dbsession.query(TechnicalRecommendation).delete()
    dbsession.query(ClimateChangeRecommendation).delete()
    dbsession.query(HazardCategoryAdministrativeDivisionAssociation).delete()
    dbsession.query(CAdHt).delete()
    dbsession.query(Contact).delete()
    dbsession.query(Region).delete()
    dbsession.query(AdministrativeDivision).delete()

    hazardtype_eq = (
        dbsession.query(HazardType).filter(HazardType.mnemonic == "EQ").one()
    )
    hazardset1 = HazardSet()
    hazardset1.id = "hazardset1"
    hazardset1.hazardtype = hazardtype_eq
    hazardset1.data_lastupdated_date = datetime.now()
    hazardset1.metadata_lastupdated_date = datetime.now()
    hazardset1.detail_url = "http://domain.com/path/"
    hazardset1.owner_organization = "data_provider"
    dbsession.add(hazardset1)

    shape = MultiPolygon([Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])])
    geometry = from_shape(shape, 4326)

    # admin_div_10 is a country (division level 1)
    admin_div_10 = AdministrativeDivision(
        **{"code": "10", "leveltype_id": 1, "name": "Division level 1"}
    )
    admin_div_10.geom = geometry
    dbsession.add(admin_div_10)

    # admin_div_11 is another country (division level 1)
    admin_div_11 = AdministrativeDivision(
        **{"code": "11", "leveltype_id": 1, "name": "Division level 1 2"}
    )
    admin_div_11.geom = geometry
    dbsession.add(admin_div_11)

    # admin_div_12 is another country (division level 1)
    admin_div_12 = AdministrativeDivision(
        **{"code": "12", "leveltype_id": 1, "name": "Division level 1 3"}
    )
    admin_div_12.geom = geometry
    dbsession.add(admin_div_12)

    # admin_div_13 is another country (division level 1)
    admin_div_13 = AdministrativeDivision(
        **{"code": "13", "leveltype_id": 1, "name": "Division level 1 4"}
    )
    admin_div_13.geom = geometry
    dbsession.add(admin_div_13)

    # admin_div_20 is a province (division level 2)
    # its parent is admin_div_10
    admin_div_20 = AdministrativeDivision(
        **{"code": "20", "leveltype_id": 2, "name": "Division level 2"}
    )
    admin_div_20.parent_code = admin_div_10.code
    admin_div_20.geom = geometry
    dbsession.add(admin_div_20)

    shape = MultiPolygon([Polygon([(0, 0), (0, 1), (0.5, 1), (0.5, 0), (0, 0)])])
    geometry = from_shape(shape, 4326)

    # admin_div_31 is a region (division level 3)
    # its parent is admin_div_20
    admin_div_31 = AdministrativeDivision(
        **{"code": "31", "leveltype_id": 3, "name": "Division level 3 - 1"}
    )
    admin_div_31.parent_code = admin_div_20.code
    admin_div_31.geom = geometry
    admin_div_31.hazardcategories = []

    shape = MultiPolygon([Polygon([(0.5, 0), (0.5, 1), (1, 1), (1, 0), (0.5, 0)])])
    geometry = from_shape(shape, 4326)

    # admin_div_32 is a region (division level 3)
    # its parent is also admin_div_20
    admin_div_32 = AdministrativeDivision(
        **{"code": "32", "leveltype_id": 3, "name": "Division level 3 - 2"}
    )
    admin_div_32.parent_code = admin_div_20.code
    admin_div_32.geom = geometry
    admin_div_32.hazardcategories = []

    # Here's a quick, graphical recap:
    #
    # admin_div_10 -> admin_div_20 -> admin_div_31
    #                             `-> admin_div_32
    # admin_div_11
    # admin_div_12
    # admin_div_13

    # GeoNode Regions
    # global_region contains all countries, **except admin_div_12**
    global_region = Region(**{"id": 1, "level": 0, "name": "Global region"})
    global_region.administrativedivisions.append(admin_div_10)
    global_region.administrativedivisions.append(admin_div_11)
    global_region.administrativedivisions.append(admin_div_13)

    # region_1 is a country
    # it matches GAULS's admin_div_10
    region_1 = Region(**{"id": 2, "level": 3, "name": "Country 1"})
    region_1.administrativedivisions.append(admin_div_10)

    # region_2 is another country
    # it matches GAULS's admin_div_11
    region_2 = Region(**{"id": 3, "level": 3, "name": "Country 2"})
    region_2.administrativedivisions.append(admin_div_11)

    # region_3 is another country
    # it matches GAULS's admin_div_12
    region_3 = Region(**{"id": 4, "level": 3, "name": "Country 3"})
    region_3.administrativedivisions.append(admin_div_12)

    # Here's a quick, graphical recap:
    #
    # global_region  -> admin_div_10 (region_1) -> admin_div_20 -> admin_div_31
    #            `                                             `-> admin_div_32
    #             `
    #              ` -> admin_div_11 (region_2)
    #               `-> admin_div_13
    #
    # region_3 = admin_div_12

    category_eq_hig = HazardCategory.get(dbsession, "EQ", "HIG")
    category_eq_hig.general_recommendation = "General recommendation for EQ HIG"

    category_fl_hig = HazardCategory.get(dbsession, "FL", "HIG")

    # admin_div_31 has (EQ, HIGH)
    association = HazardCategoryAdministrativeDivisionAssociation(
        **{"hazardcategory": category_eq_hig}
    )
    association.hazardsets.append(hazardset1)
    admin_div_31.hazardcategories.append(association)

    # admin_div_31 has (RF, HIGH)
    admin_div_32.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(
            **{"hazardcategory": category_fl_hig}
        )
    )

    # admin_div_32 has (EQ, HIGH)
    admin_div_32.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(
            **{"hazardcategory": category_eq_hig}
        )
    )

    # admin_div_10 has (EQ, HIGH)
    admin_div_10.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(
            **{"hazardcategory": category_eq_hig}
        )
    )

    # admin_div_11 has no category (this is tested)
    # admin_div_12 has (EQ, HIGH)
    admin_div_12.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(
            **{"hazardcategory": category_eq_hig}
        )
    )

    # admin_div_13 has (EQ, HIGH)
    admin_div_13.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(
            **{"hazardcategory": category_eq_hig}
        )
    )

    climate_rec = ClimateChangeRecommendation(
        text="Climate change recommendation", hazardtype=HazardType.get(dbsession, "EQ")
    )
    climate_rec.associations.append(
        CcrAd(administrativedivision=admin_div_10, hazardtype=HazardType.get(dbsession, "EQ"))
    )
    dbsession.add(climate_rec)

    climate_rec = ClimateChangeRecommendation(
        text="Climate change recommendation 2", hazardtype=HazardType.get(dbsession, "EQ")
    )
    climate_rec.associations.append(
        CcrAd(administrativedivision=admin_div_11, hazardtype=HazardType.get(dbsession, "EQ"))
    )
    dbsession.add(climate_rec)

    technical_rec = TechnicalRecommendation(
        **{
            "text": "Recommendation #1 for earthquake, applied to"
            " hazard categories HIG, MED and LOW"
        }
    )
    association = HazardCategoryTechnicalRecommendationAssociation(order=1)
    association.hazardcategory = category_eq_hig
    technical_rec.hazardcategory_associations.append(association)
    dbsession.add(technical_rec)

    technical_rec = TechnicalRecommendation(
        **{"text": "Educational web resources on earthquakes and" " seismic hazard"}
    )
    association = HazardCategoryTechnicalRecommendationAssociation(order=1)
    association.hazardcategory = category_eq_hig
    technical_rec.hazardcategory_associations.append(association)
    dbsession.add(technical_rec)

    category_fl_med = HazardCategory.get(dbsession, "FL", "MED")
    category_fl_med.general_recommendation = "General recommendation for FL MED"

    admin_div_31.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(
            **{"hazardcategory": category_fl_med}
        )
    )
    dbsession.add(admin_div_31)
    admin_div_32.hazardcategories.append(
        HazardCategoryAdministrativeDivisionAssociation(
            **{"hazardcategory": category_fl_med}
        )
    )
    dbsession.add(admin_div_32)

    # generic further resource for EQ:
    # it should be found on every EQ report page
    # (except admin_div_12 which is not linked with global region)
    further_resource = FurtherResource(
        **{
            "text": "Educational web resources on earthquakes and" + " seismic hazard",
            "id": 3,
        }
    )
    association = HazardTypeFurtherResourceAssociation()
    association.hazardtype = hazardtype_eq
    association.region = global_region
    further_resource.hazardtype_associations.append(association)
    dbsession.add(further_resource)

    # further resource for EQ & region 1:
    # it should be found only on region 1 (and sub-divisions) page
    further_resource = FurtherResource(
        **{"text": "Further resource for earthquake for region 1", "id": 5}
    )
    association = HazardTypeFurtherResourceAssociation()
    association.hazardtype = hazardtype_eq
    association.region = region_1
    further_resource.hazardtype_associations.append(association)
    dbsession.add(further_resource)

    # contact for EQ & admin_div_11:
    contact1 = Contact(
        **{
            "name": "Contact name",
            "url": "http://domain.com",
            "phone": "0123456789",
            "email": "mail@domain.com",
        }
    )
    dbsession.add(contact1)
    association = CAdHt()
    association.hazardtype = hazardtype_eq
    association.administrativedivision = admin_div_10
    association.contact = contact1
    dbsession.add(association)

    # contact for EQ & admin_div_11:
    contact2 = Contact(
        **{
            "name": "Contact name 2",
            "url": "http://domain.com",
            "phone": "0123456789",
            "email": "mail@domain.com",
        }
    )
    dbsession.add(contact1)
    association = CAdHt()
    association.hazardtype = hazardtype_eq
    association.administrativedivision = admin_div_10
    association.contact = contact2
    dbsession.add(association)

    Publication.new(dbsession)

    dbsession.flush()
