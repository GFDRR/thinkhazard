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

from markdown import markdown
from pyramid.threadlocal import get_current_request
from jinja2 import contextfilter
from pyramid.i18n import get_localizer, TranslationStringFactory


def markdown_filter(text):
    return markdown(text)


@contextfilter
def translate(ctx, text, *elements, **kw):
    request = ctx.get('request') or get_current_request()
    tsf = TranslationStringFactory('thinkhazard-database')
    localizer = get_localizer(request)
    return localizer.translate(tsf(text))
