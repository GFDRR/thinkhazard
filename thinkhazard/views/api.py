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

from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPNotFound,
    )

from .admin import (
    admindiv_hazardsets_hazardtype,
)

from ..models import (
    DBSession,
    HazardCategory,
    HazardType,
    HazardLevel,
    )

cors_policy = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
}


def cors_headers(cors_policy):

    def add_cors_headers(view_callable):

        def wrapper(context, request):
            request.response.headers.update(cors_policy)
            return view_callable(context, request)

        return wrapper

    return add_cors_headers


@view_config(route_name='api_hazardcategory',
             decorator=cors_headers(cors_policy),
             renderer='json')
def api_hazardcategory(request):
    hazard_type = request.matchdict['hazard_type']
    hazard_level = request.matchdict['hazard_level']

    try:
        hazard_category = DBSession.query(HazardCategory) \
            .join(HazardType) \
            .join(HazardLevel) \
            .filter(HazardType.mnemonic == hazard_type) \
            .filter(HazardLevel.mnemonic == hazard_level) \
            .one()
    except:
        raise HTTPNotFound()

    return {
        'hazard_category': hazard_category
    }


@view_config(route_name='api_admindiv_hazardsets_hazardtype',
             decorator=cors_headers(cors_policy),
             renderer='json')
def api_admindiv_hazardsets_hazardtype(request):
    data = admindiv_hazardsets_hazardtype(request)
    return data
