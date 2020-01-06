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

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from ..models import (
    DBSession,
    AdministrativeDivision as AdDiv,
    AdminLevelType,
    )

from sqlalchemy import (
    func,
    or_,
    and_,
    )


@view_config(route_name='administrativedivision', renderer='json')
def administrativedivision(request):

    if 'q' not in request.params:
        raise HTTPBadRequest(detail='parameter "q" is missing')

    term = request.params['q']

    filter_lang = None

    if request.locale_name != 'en':
        attribute = getattr(AdDiv, 'name_' + request.locale_name)
        filter_lang = func.unaccent(attribute) \
            .ilike(func.unaccent('%{}%'.format(term)))
        filter_lang = and_(
            filter_lang,
            AdminLevelType.mnemonic == 'COU')

    filter = func.unaccent(AdDiv.name) \
        .ilike(func.unaccent('%{}%'.format(term)))

    if filter_lang is not None:
        filter = or_(filter_lang, filter)

    query = DBSession.query(AdDiv) \
        .filter(filter) \
        .join(AdminLevelType) \
        .order_by(
            AdDiv.name.ilike(term).desc(),
            AdDiv.name.ilike('{}%'.format(term)).desc(),
            AdDiv.leveltype_id,
            AdDiv.name) \
        .limit(10)
    data = query.all()

    return {'data': data}
