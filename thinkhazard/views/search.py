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
from pyramid.httpexceptions import HTTPBadRequest

from ..models import (
    DBSession,
    AdministrativeDivision,
    )

from sqlalchemy import (
    func,
    )


@view_config(route_name='administrativedivision', renderer='json')
def administrativedivision(request):

    if 'q' not in request.params:
        raise HTTPBadRequest(detail='parameter "q" is missing')

    term = request.params['q']

    query = DBSession.query(AdministrativeDivision) \
        .filter(
            func.unaccent(AdministrativeDivision.name)
                .ilike(func.unaccent(u'%{}%'.format(term)))) \
        .order_by(
            AdministrativeDivision.name.ilike(term).desc(),
            AdministrativeDivision.name.ilike(u'{}%'.format(term)).desc(),
            AdministrativeDivision.leveltype_id,
            AdministrativeDivision.name) \
        .limit(10)
    data = query.all()

    return {'data': data}
