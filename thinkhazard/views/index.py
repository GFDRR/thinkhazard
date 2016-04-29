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

from ..models import (
    DBSession,
    HazardType,
    Publication,
    )


@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    return {'hazards': hazard_types}


@view_config(route_name='about', renderer='templates/about.jinja2')
def about(request):
    publication_date = Publication.last()
    return {
        'publication_date': (publication_date.date.strftime('%c')
                             if publication_date else '')
    }


@view_config(route_name='faq', renderer='templates/faq.jinja2')
def faq(request):
    return {}
