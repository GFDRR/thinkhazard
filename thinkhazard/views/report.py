import itertools
import geoalchemy2.shape

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from sqlalchemy.orm import aliased
from sqlalchemy import and_

from geoalchemy2.shape import to_shape

from ..models import (
    DBSession,
    AdminLevelType,
    AdministrativeDivision,
    CategoryType,
    HazardCategory,
    HazardType)


# An object for the "no data" category type.
_categorytype_nodata = CategoryType()
_categorytype_nodata.mnemonic = 'no-data'
_categorytype_nodata.title = 'No data available'
_categorytype_nodata.description = 'No data for this hazard type.'
_categorytype_nodata.order = float('inf')


@view_config(route_name='report_overview', renderer='templates/report.jinja2')
@view_config(route_name='report', renderer='templates/report.jinja2')
def report(request):
    try:
        division_code = request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    hazard = request.matchdict.get('hazardtype', None)

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

    if hazard is not None:
        hazard = hazard_data[hazard]
    # Order the hazard data by category type (hazard types with the highest
    # risk are first in the UI).
    hazard_data = hazard_data.values()
    hazard_data = sorted(hazard_data, key=lambda d: d['categorytype'].order)

    # Get the geometry for division and compute its extent
    division_shape = geoalchemy2.shape.to_shape(division.geom)
    division_bounds = list(division_shape.bounds)

    return {'hazards': hazard_data,
            'hazard': hazard,
            'division': division,
            'bounds': division_bounds,
            'parent_division': division.parent}


@view_config(route_name='report_json', renderer='geojson')
@view_config(route_name='report_overview_json', renderer='geojson')
def report_json(request):

    try:
        division_code = request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    hazard_type = request.matchdict.get('hazardtype', None)

    division_leveltype, = DBSession.query(AdminLevelType.mnemonic) \
        .join(AdministrativeDivision.leveltype) \
        .filter(AdministrativeDivision.code == division_code).one()

    _filter = None
    if division_leveltype == u'REG':
        _filter = AdministrativeDivision.code == division_code
    else:
        _filter = AdministrativeDivision.parent_code == division_code

    if hazard_type is not None:
        subdivisions = DBSession.query(AdministrativeDivision) \
            .add_columns(CategoryType.mnemonic) \
            .outerjoin(AdministrativeDivision.hazardcategories) \
            .outerjoin(HazardType)\
            .outerjoin(CategoryType) \
            .filter(and_(_filter, HazardType.mnemonic == hazard_type))
    else:
        subdivisions = itertools.izip(
            DBSession.query(AdministrativeDivision).filter(_filter),
            itertools.cycle(('NONE',)))

    return [{
        'type': 'Feature',
        'geometry': to_shape(subdivision.geom),
        'properties': {
            'name': subdivision.name,
            'code': subdivision.code,
            'hazardLevel': categorytype
            }
        } for subdivision, categorytype in subdivisions]
