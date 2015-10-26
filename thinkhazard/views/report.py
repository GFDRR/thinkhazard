from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound

from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import and_, or_, null, select
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal_column

from geoalchemy2.shape import to_shape


from ..models import (
    DBSession,
    AdministrativeDivision,
    HazardLevel,
    HazardCategory,
    HazardType,
    ClimateChangeRecommendation,
    TechnicalRecommendation,
    HazardCategoryTechnicalRecommendationAssociation,
)
    #AdditionalInformationType,)


# An object for the "no data" category type.
_hazardlevel_nodata = HazardLevel()
_hazardlevel_nodata.mnemonic = 'no-data'
_hazardlevel_nodata.title = 'No data available'
_hazardlevel_nodata.description = 'No data for this hazard type.'
_hazardlevel_nodata.order = float('inf')


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
    hazardtype_query = DBSession.query(HazardType).order_by(HazardType.order)

    # Get the hazard categories corresponding to the administrative
    # division whose code is division_code.
    hazardcategories_query = DBSession.query(HazardCategory) \
        .join(HazardCategory.administrativedivisions) \
        .join(HazardType) \
        .join(HazardLevel) \
        .filter(AdministrativeDivision.code == division_code)

    # Create a dict with the categories. Keys are the hazard type mnemonic.
    hazardcategories = {d.hazardtype.mnemonic: d
                        for d in hazardcategories_query}

    hazard_types = []
    for hazardtype in hazardtype_query:
        cat = _hazardlevel_nodata
        if hazardtype.mnemonic in hazardcategories:
            cat = hazardcategories[hazardtype.mnemonic].hazardlevel
        hazard_types.append({
            'hazardtype': hazardtype,
            'hazardlevel': cat
        })

    hazard_category = None
    resources = None
    technical_recommendations = None
    climate_change_recommendation = None

    if hazard is not None:
        try:
            hazard_category = DBSession.query(HazardCategory) \
                .join(HazardCategory.administrativedivisions) \
                .join(HazardLevel) \
                .join(HazardType) \
                .filter(HazardType.mnemonic == hazard) \
                .filter(AdministrativeDivision.code == division_code) \
                .one()
        except NoResultFound:
            url = request.route_url('report_overview',
                divisioncode=division_code)
            return HTTPFound(location=url)

        try:
            climate_change_recommendation = DBSession.query(
                    ClimateChangeRecommendation) \
                .join(AdministrativeDivision) \
                .join(HazardType) \
                .filter(AdministrativeDivision.code == division_code) \
                .filter(HazardType.mnemonic == hazard) \
                .one()
        except NoResultFound:
            pass

        technical_recommendations = DBSession.query(TechnicalRecommendation) \
            .join(TechnicalRecommendation.hazardcategory_associations) \
            .join(HazardCategory) \
            .filter(HazardCategory.id == hazard_category.id) \
            .filter(or_(AdministrativeDivision.code == division_code,
                        AdministrativeDivision.code == null())) \
            .all()

        #resources = filter(
            #lambda x: x.type.mnemonic == 'AVD',
            #additional_informations)

        #recommendations = filter(
            #lambda x: x.type.mnemonic == 'REC',
            #additional_informations)

    # Get the administrative division whose code is division_code.
    _alias = aliased(AdministrativeDivision)
    division = DBSession.query(AdministrativeDivision) \
        .outerjoin(_alias, _alias.code == AdministrativeDivision.parent_code) \
        .filter(AdministrativeDivision.code == division_code).one()

    # Get the geometry for division and compute its extent
    cte = select([
        func.ST_Transform(AdministrativeDivision.geom, 4326).label('geom')]) \
        .where(AdministrativeDivision.code == division_code) \
        .cte('bounds')
    bounds = list(DBSession.query(
        func.ST_XMIN(cte.c.geom),
        func.ST_YMIN(cte.c.geom),
        func.ST_XMAX(cte.c.geom),
        func.ST_YMAX(cte.c.geom))
        .one())
    division_bounds = bounds

    # compute a 0-360 version of the extent
    cte = select([
        func.ST_Shift_Longitude(
            func.ST_Transform(AdministrativeDivision.geom, 4326)
        ).label('shift')]) \
        .where(AdministrativeDivision.code == division_code) \
        .cte('bounds')
    bounds_shifted = list(DBSession.query(
        func.ST_XMIN(cte.c.shift),
        func.ST_YMIN(cte.c.shift),
        func.ST_XMAX(cte.c.shift),
        func.ST_YMAX(cte.c.shift))
        .one())

    # Use the 0-360 if it's smaller
    if bounds_shifted[2] - bounds_shifted[0] < bounds[2] - bounds[0]:
        division_bounds = bounds_shifted

    parents = []
    if division.leveltype_id >= 2:
        parents.append(division.parent)
    if division.leveltype_id == 3:
        parents.append(division.parent.parent)

    return {'hazards': hazard_types,
            'hazard_category': hazard_category,
            'climate_change_recommendation': climate_change_recommendation,
            #'resources': resources,
            'recommendations': technical_recommendations,
            'division': division,
            'bounds': division_bounds,
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
            .add_columns(simplify, HazardLevel.mnemonic) \
            .outerjoin(AdministrativeDivision.hazardcategories) \
            .outerjoin(HazardType)\
            .outerjoin(HazardLevel) \
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
            'hazardLevel': hazardlevel
        }
    } for division, geom_simplified, hazardlevel in divisions]
