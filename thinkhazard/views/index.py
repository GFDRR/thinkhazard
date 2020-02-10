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
from pyramid.i18n import get_localizer, TranslationStringFactory

from ..models import DBSession, HazardType, Publication


@view_config(route_name="index", renderer="templates/index.jinja2")
def index(request):
    hazard_types = (
        DBSession.query(HazardType)
        .order_by(HazardType.order)
        .filter(HazardType.ready.isnot(False))
    )

    return {
        "hazards": hazard_types,
        "feedback_form_url": request.registry.settings["feedback_form_url"],
    }


@view_config(route_name="about", renderer="templates/about.jinja2")
@view_config(route_name="pdf_about", renderer="templates/pdf_about.jinja2")
def about(request):
    publication_date = Publication.last()
    return {
        "publication_date": (
            publication_date.date.strftime("%c") if publication_date else ""
        )
    }


@view_config(route_name="faq", renderer="templates/faq.jinja2")
def faq(request):
    return {}


@view_config(route_name="disclaimer", renderer="templates/disclaimer.jinja2")
def disclaimer(request):
    return {"feedback_form_url": request.registry.settings["feedback_form_url"]}


@view_config(route_name="data_map", renderer="templates/data_map.jinja2")
def data_map(request):
    tsf = TranslationStringFactory("thinkhazard")
    localizer = get_localizer(request)

    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    types = [(h.mnemonic, localizer.translate(tsf(h.title))) for h in hazard_types]
    return {"hazard_types": types}
