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

import unicodedata

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from thinkhazard.models import AdministrativeDivision as AdDiv, AdminLevelType

from sqlalchemy import and_, case, func, or_


def _normalize(text):
    if not text:
        return ""
    return (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
    )


@view_config(route_name="administrativedivision", renderer="json")
def administrativedivision(request):

    if "q" not in request.params:
        raise HTTPBadRequest(detail='parameter "q" is missing')
    term = request.params["q"]

    # Search in all language fields
    term_pattern = "%{}%".format(term)
    filter = or_(
        func.unaccent(AdDiv.name).ilike(func.unaccent(term_pattern)),
        func.unaccent(AdDiv.name_en).ilike(func.unaccent(term_pattern)),
        func.unaccent(AdDiv.name_fr).ilike(func.unaccent(term_pattern)),
        func.unaccent(AdDiv.name_es).ilike(func.unaccent(term_pattern)),
    )

    # Priority: Country > Capital > GHSL Urban Center > Other
    type_priority = case(
        (AdDiv.leveltype_id == 1, 1),
        (and_(AdDiv.leveltype_id == 4, AdDiv.is_capital == True), 2),  # noqa: E712
        (AdDiv.leveltype_id == 4, 3),
        else_=4,
    )

    query = (
        request.dbsession.query(AdDiv)
        .filter(filter)
        .join(AdminLevelType)
        .order_by(
            type_priority,
            AdDiv.name.ilike(term).desc(),
            AdDiv.name_en.ilike(term).desc(),
            AdDiv.name_fr.ilike(term).desc(),
            AdDiv.name_es.ilike(term).desc(),
            AdDiv.name.ilike("{}%".format(term)).desc(),
            AdDiv.name_en.ilike("{}%".format(term)).desc(),
            AdDiv.name_fr.ilike("{}%".format(term)).desc(),
            AdDiv.name_es.ilike("{}%".format(term)).desc(),
            AdDiv.leveltype_id,
            AdDiv.name,
        )
        .limit(10)
    )

    def get_matched_lang(div):
        n_term = _normalize(term)
        if div.name and n_term in _normalize(div.name):
            return None
        for lang in [request.locale_name, "en", "fr", "es"]:
            attr = "name_" + lang
            val = getattr(div, attr, None)
            if val and n_term in _normalize(val):
                return lang
        return request.locale_name

    data = query.all()
    for div in data:
        div._matched_lang = get_matched_lang(div)

    return {"data": data}
