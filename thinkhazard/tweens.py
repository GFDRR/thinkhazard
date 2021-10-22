# -*- coding: utf-8 -*-
#
# Copyright (C) 2015- by the GFDRR / World Bank
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

import pytz
from functools import partial
import secure
from pyramid.response import Response
from pyramid.renderers import render
from pyramid.httpexceptions import HTTPNotModified

from .models import Publication


def set_secure_headers(handler, registry):
    """
    Returns tween which add security headers to responses.
    """

    def tween(request, secure_headers):
        response = handler(request)
        secure_headers.framework.pyramid(response)
        return response

    csp = (
        secure.ContentSecurityPolicy()
        .default_src("'self'")
        .script_src(
            "'self'",
            "'unsafe-inline'",
            "https://www.google-analytics.com",
            "https://cdnjs.cloudflare.com",
        )
        .style_src("'self'", "https://fonts.googleapis.com")
        .font_src("'self'", "https://fonts.gstatic.com")
        .img_src(
            "'self'",
            "data:",
            "https://www.gfdrr.org",
            "http://www.geonode-gfdrrlab.org",
            "https://api.mapbox.com",
        )
        .connect_src("'self'", "https://www.google-analytics.com")
    )

    hsts = secure.StrictTransportSecurity().max_age(31536000).include_subdomains()

    if registry.settings["appname"] == "public":
        return partial(
            tween,
            secure_headers=secure.Secure(
                cache=secure.CacheControl().public(),
                csp=csp,
                hsts=hsts,
            )
        )

    else:
        return partial(
            tween,
            secure_headers=secure.Secure(
                csp=csp,
                hsts=hsts,
            )
        )

    return tween


def notmodified_tween_factory(handler, registry):

    if registry.settings["appname"] == "public":

        gmt = pytz.timezone("GMT")

        def notmodified_tween(request):
            if request.path == "/healthcheck":
                return handler(request)

            publication_date = gmt.localize(Publication.last(request.dbsession).date)

            if False:
                response = Response(render("templates/maintenance.jinja2", {}, request))
                response.status_code = 503
                return response

            if (
                request.if_modified_since is not None
                and request.if_modified_since >= publication_date.replace(microsecond=0)
            ):
                return HTTPNotModified()

            request.publication_date = publication_date
            response = handler(request)
            response.last_modified = publication_date

            return response

        return notmodified_tween

    if registry.settings["appname"] == "admin":

        def nocache_tween(request):
            response = handler(request)
            response.cache_expires(0)
            return response

        return nocache_tween

    return handler
