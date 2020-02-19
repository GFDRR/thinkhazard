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

from thinkhazard.models import AdministrativeDivision, Publication


@view_config(route_name="sitemap", renderer="templates/sitemap.jinja2")
def sitemap(request):
    divisions = request.dbsession.query(AdministrativeDivision)
    request.response.content_type = "application/xml"
    return {
        "divisions": divisions.all(),
        "publication_date": Publication.last(request.dbsession).date.strftime("%Y-%m-%d"),
    }
