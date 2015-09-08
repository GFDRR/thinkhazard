from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from sqlalchemy.orm import aliased
from sqlalchemy import and_, or_, null
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal_column

from geoalchemy2.shape import to_shape


from ..models import (
    DBSession,
    AdministrativeDivision,
    CategoryType,
    HazardCategory,
    HazardType,
    AdditionalInformation,
    AdditionalInformationType,)


# An object for the "no data" category type.
_categorytype_nodata = CategoryType()
_categorytype_nodata.mnemonic = 'no-data'
_categorytype_nodata.title = 'No data available'
_categorytype_nodata.description = 'No data for this hazard type.'
_categorytype_nodata.order = float('inf')


@view_config(route_name='report_overview', renderer='templates/report.jinja2')
@view_config(route_name='report_overview_slash',
             renderer='templates/report.jinja2')
@view_config(route_name='report', renderer='templates/report.jinja2')
def report(request):
    try:
        division_code = request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    hazard = request.matchdict.get('hazardtype', None)

    # Get all the hazard types.
    hazardtype_query = DBSession.query(HazardType)

    # Create a dict containing the data sent to the report template. The keys
    # are the hazard type mnemonics.
    hazard_types = {hazardtype.mnemonic: {'hazardtype': hazardtype,
                                          'categorytype': _categorytype_nodata}
                    for hazardtype in hazardtype_query}

    # Get the hazard categories corresponding to the administrative
    # division whose code is division_code.
    hazardcategories = DBSession.query(HazardCategory) \
        .join(HazardCategory.administrativedivisions) \
        .join(HazardType) \
        .join(CategoryType) \
        .filter(AdministrativeDivision.code == division_code)

    # Udpate the data (hazard_types).
    for hazardcategory in hazardcategories:
        key = hazardcategory.hazardtype.mnemonic
        hazard_types[key]['categorytype'] = hazardcategory.categorytype

    # Order the hazard data by category type (hazard types with the highest
    # risk are first in the UI).
    hazard_types = hazard_types.values()
    hazard_types = sorted(hazard_types, key=lambda d: d['categorytype'].order)

    hazard_category = None
    resources = None
    recommendations = None

    if hazard is not None:
        hazard_category = DBSession.query(HazardCategory) \
            .join(HazardCategory.administrativedivisions) \
            .join(CategoryType) \
            .join(HazardType) \
            .filter(HazardType.mnemonic == hazard) \
            .filter(AdministrativeDivision.code == division_code) \
            .one()

        additional_informations = DBSession.query(AdditionalInformation) \
            .join(AdditionalInformation.hazardcategory_associations) \
            .join(HazardCategory) \
            .join(AdditionalInformationType) \
            .outerjoin(AdditionalInformation.administrativedivisions) \
            .filter(HazardCategory.id == hazard_category.id) \
            .filter(or_(AdministrativeDivision.code == division_code,
                        AdministrativeDivision.code == null())) \
            .all()

        resources = filter(
            lambda x: x.type.mnemonic == 'AVD',
            additional_informations)

        recommendations = filter(
            lambda x: x.type.mnemonic == 'REC',
            additional_informations)

    # Get the administrative division whose code is division_code.
    _alias = aliased(AdministrativeDivision)
    division = DBSession.query(AdministrativeDivision) \
        .outerjoin(_alias, _alias.code == AdministrativeDivision.parent_code) \
        .filter(AdministrativeDivision.code == division_code).one()

    # Get the geometry for division and compute its extent
    bounds = func.ST_Shift_Longitude(
            func.ST_Transform(AdministrativeDivision.geom, 4326))
    division_bounds = DBSession.query(
        func.ST_XMIN(bounds),
        func.ST_YMIN(bounds),
        func.ST_XMAX(bounds),
        func.ST_YMAX(bounds)) \
        .filter(AdministrativeDivision.code == division_code) \
        .one()

    parents = []
    if division.leveltype_id >= 2:
        parents.append(division.parent)
    if division.leveltype_id == 3:
        parents.append(division.parent.parent)

    return {'hazards': hazard_types,
            'hazard_category': hazard_category,
            'resources': resources,
            'recommendations': recommendations,
            'division': division,
            'bounds': list(division_bounds),
            'parents': parents,
            'parent_division': division.parent}


@view_config(route_name='report_json', renderer='geojson')
@view_config(route_name='report_overview_json', renderer='geojson')
def report_json(request):

    try:
        division_code = request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    try:
        resolution = float(request.params.get('resolution'))
    except:
        raise HTTPBadRequest(detail='invalid value for parameter "resolution"')

    hazard_type = request.matchdict.get('hazardtype', None)

    _filter = or_(AdministrativeDivision.code == division_code,
                  AdministrativeDivision.parent_code == division_code)

    simplify = func.ST_Simplify(AdministrativeDivision.geom, resolution / 2)

    if hazard_type is not None:
        divisions = DBSession.query(AdministrativeDivision) \
            .add_columns(simplify, CategoryType.mnemonic) \
            .outerjoin(AdministrativeDivision.hazardcategories) \
            .outerjoin(HazardType)\
            .outerjoin(CategoryType) \
            .filter(and_(_filter, HazardType.mnemonic == hazard_type))
    else:
        divisions = DBSession.query(AdministrativeDivision) \
            .add_columns(simplify, literal_column("'None'")) \
            .filter(_filter)

    return [{
        'type': 'Feature',
        'geometry': to_shape(geom_simplified),
        'properties': {
            'name': division.name,
            'code': division.code,
            'hazardLevel': categorytype
        }
    } for division, geom_simplified, categorytype in divisions]
