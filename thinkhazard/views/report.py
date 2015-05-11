from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from sqlalchemy.orm import aliased

from ..models import (
    DBSession,
    AdministrativeDivision,
    CategoryType,
    HazardCategory,
    HazardCategoryRecommendationAssociation,
    HazardCategoryAdditionalInformationAssociation,
    HazardType)


# An object for the "no data" category type.
_categorytype_nodata = CategoryType()
_categorytype_nodata.mnemonic = 'no-data'
_categorytype_nodata.title = 'No data'
_categorytype_nodata.description = 'No data for this hazard type.'
_categorytype_nodata.order = float('inf')


@view_config(route_name='report', renderer='templates/report.jinja2')
def report(request):
    try:
        division_code = int(request.params.get('divisioncode'))
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    # Query 1: get the administrative division whose code is division_code.
    _alias = aliased(AdministrativeDivision)
    division = DBSession.query(AdministrativeDivision) \
        .outerjoin(_alias, _alias.code == AdministrativeDivision.parent_code) \
        .filter(AdministrativeDivision.code == division_code).one()

    # Query 2: get all the hazard types.
    hazardtype_query = DBSession.query(HazardType)

    # Create a dict containing the data sent to the report template. The keys
    # are the hazard type mnemonics.
    hazard_data = {hazardtype.mnemonic: {'hazardtype': hazardtype,
                                         'categorytype': _categorytype_nodata,
                                         'description': None,
                                         'recommendation_associations': None,
                                         'additionalinfo_associations': None}
                   for hazardtype in hazardtype_query}

    # Query 3: get the hazard categories corresponding to the administrative
    # division whose code is division_code.
    hazardcategories = DBSession.query(HazardCategory) \
        .join(HazardCategory.administrativedivisions) \
        .join(HazardCategory.recommendation_associations) \
        .join(HazardCategoryRecommendationAssociation.recommendation) \
        .join(HazardCategory.additionalinformation_associations) \
        .join(HazardCategoryAdditionalInformationAssociation
              .additionalinformation) \
        .join(HazardType) \
        .join(CategoryType) \
        .filter(AdministrativeDivision.code == division_code)

    # Udpate the data (hazard_data).
    for hazardcategory in hazardcategories:
        key = hazardcategory.hazardtype.mnemonic
        hazard_data[key]['categorytype'] = hazardcategory.categorytype
        hazard_data[key]['description'] = hazardcategory.description
        hazard_data[key]['recommendation_associations'] = \
            hazardcategory.recommendation_associations
        hazard_data[key]['additionalinfo_associations'] = \
            hazardcategory.additionalinformation_associations

    # Order the hazard data by category type (hazard types with the highest
    # risk are first in the UI).
    hazard_data = hazard_data.values()
    hazard_data = sorted(hazard_data, key=lambda d: d['categorytype'].order)

    return {'hazards': hazard_data, 'division': division,
            'parent_division': division.parent}
