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

import urllib
import datetime

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound

from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import and_, or_, select
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal_column

from geoalchemy2.shape import to_shape
from urlparse import urlunsplit

from ..processing import settings

from ..models import (
    DBSession,
    AdministrativeDivision,
    HazardLevel,
    HazardCategory,
    HazardType,
    Region,
    ClimateChangeRecommendation,
    ClimateChangeRecAdministrativeDivisionAssociation as CcrAd,
    TechnicalRecommendation,
    FurtherResource,
    HazardCategoryAdministrativeDivisionAssociation,
    HazardCategoryTechnicalRecommendationAssociation,
)


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
@view_config(route_name='report_print',
             renderer='templates/pdf_report.jinja2')
def report(request):
    try:
        division_code = request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    selected_hazard = request.matchdict.get('hazardtype', None)

    hazard_types = get_hazard_types(division_code)

    hazard_category = None

    division = get_division(division_code)

    if selected_hazard is not None:
        try:
            hazard_category = get_info_for_hazard_type(selected_hazard,
                                                       division)
        except NoResultFound:
            url = request.route_url('report_overview',
                                    divisioncode=division.code)
            return HTTPFound(location=url)
    # Get the geometry for division and compute its extent
    cte = select([AdministrativeDivision.geom]) \
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
        func.ST_Translate(
            func.ST_Shift_Longitude(
                func.ST_Translate(AdministrativeDivision.geom, 180, 0)),
            -180, 0).label('shift')]) \
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

    feedback_params = {}
    feedback_params['entry.1144401731'] = str(division.code) + ' - ' + \
        division.name
    if selected_hazard is not None:
        feedback_params['entry.93444540'] = \
            HazardType.get(selected_hazard).title

    feedback_form_url = settings['feedback_form_url'] + '?' + \
        urllib.urlencode(feedback_params)

    context = {
        'hazards': hazard_types,
        'hazards_sorted': sorted(
            hazard_types, key=lambda a: a['hazardlevel'].order),
        'division': division,
        'bounds': division_bounds,
        'parents': get_parents(division),
        'parent_division': division.parent,
        'date': datetime.datetime.now(),
        'feedback_form_url': feedback_form_url,
    }
    if hazard_category is not None:
        context.update(hazard_category)
    return context


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

    simplify = func.ST_Simplify(
        func.ST_Transform(AdministrativeDivision.geom, 3857), resolution / 2)

    if hazard_type is not None:
        divisions = DBSession.query(AdministrativeDivision) \
            .add_columns(simplify, HazardLevel.mnemonic, HazardLevel.title) \
            .outerjoin(AdministrativeDivision.hazardcategories) \
            .join(HazardCategory) \
            .outerjoin(HazardType)\
            .outerjoin(HazardLevel) \
            .filter(and_(_filter, HazardType.mnemonic == hazard_type))
    else:
        divisions = DBSession.query(AdministrativeDivision) \
            .add_columns(simplify, literal_column("'None'"),
                         literal_column("'blah'")) \
            .filter(_filter)

    return [{
        'type': 'Feature',
        'geometry': to_shape(geom_simplified),
        'properties': {
            'name': division.name,
            'code': division.code,
            'hazardLevelMnemonic': hazardlevel_mnemonic,
            'hazardLevelTitle': hazardlevel_title
        }
    } for division, geom_simplified, hazardlevel_mnemonic,
          hazardlevel_title in divisions]


def get_parents(division):
    parents = []
    if division.leveltype_id >= 2:
        parents.append(division.parent)
    if division.leveltype_id == 3:
        parents.append(division.parent.parent)
    return parents


def get_division(code):
    # Get the administrative division whose code is division_code.
    _alias = aliased(AdministrativeDivision)
    return DBSession.query(AdministrativeDivision) \
        .outerjoin(_alias, _alias.code == AdministrativeDivision.parent_code) \
        .filter(AdministrativeDivision.code == code).one()


def get_hazard_types(code):

    # Get all the hazard types.
    hazardtype_query = DBSession.query(HazardType).order_by(HazardType.order)

    # Get the hazard categories corresponding to the administrative
    # division whose code is division_code.
    hazardcategories_query = DBSession.query(HazardCategory) \
        .join(HazardCategoryAdministrativeDivisionAssociation) \
        .join(AdministrativeDivision) \
        .join(HazardType) \
        .join(HazardLevel) \
        .filter(AdministrativeDivision.code == code)

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
    return hazard_types


def get_info_for_hazard_type(hazard_type, division):
    technical_recommendations = None
    further_resources = None
    sources = None
    climate_change_recommendation = None

    hazard_category = DBSession.query(HazardCategory) \
        .join(HazardCategoryAdministrativeDivisionAssociation) \
        .join(AdministrativeDivision) \
        .join(HazardLevel) \
        .join(HazardType) \
        .filter(HazardType.mnemonic == hazard_type) \
        .filter(AdministrativeDivision.code == division.code) \
        .one()

    # get the code for level 0 division
    code = division.code
    if division.leveltype_id == 2:
        code = division.parent.code
    if division.leveltype_id == 3:
        code = division.parent.parent.code
    climate_change_recommendation = DBSession.query(
            ClimateChangeRecommendation) \
        .join(CcrAd) \
        .join(HazardType) \
        .join(AdministrativeDivision) \
        .filter(AdministrativeDivision.code == code) \
        .filter(HazardType.mnemonic == hazard_type) \
        .one_or_none()

    technical_recommendations = DBSession.query(TechnicalRecommendation) \
        .join(TechnicalRecommendation.hazardcategory_associations) \
        .join(HazardCategory) \
        .filter(HazardCategory.id == hazard_category.id) \
        .order_by(HazardCategoryTechnicalRecommendationAssociation.order) \
        .all()

    further_resources_query = DBSession.query(FurtherResource) \
        .join(FurtherResource.hazardtype_associations) \
        .join(HazardType) \
        .join(Region) \
        .join(Region.administrativedivisions) \
        .filter(HazardType.id == hazard_category.hazardtype.id) \
        .filter(AdministrativeDivision.code == code) \
        .order_by(Region.level.desc())
    # "first class" documents relate directly with the country
    # "second class" documents do not relate directly with the country,
    # they appear lower in the page

    further_resources = []
    for fr in further_resources_query:
        further_resources.append({
            'id': fr.id,
            'text': fr.text,
            'url': urlunsplit((settings['geonode']['scheme'],
                               settings['geonode']['netloc'],
                               'documents/{}/download'.format(fr.id),
                               '', ''))
        })

    sources = DBSession.query(
            HazardCategoryAdministrativeDivisionAssociation) \
        .join(AdministrativeDivision) \
        .join(HazardCategory) \
        .filter(HazardCategory.id == hazard_category.id) \
        .filter(AdministrativeDivision.code == division.code) \
        .one() \
        .hazardsets

    return {
        'hazard_category': hazard_category,
        'climate_change_recommendation': climate_change_recommendation,
        'recommendations': technical_recommendations,
        'resources': further_resources,
        'sources': sources,
    }
