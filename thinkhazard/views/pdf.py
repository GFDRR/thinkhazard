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

import datetime
import logging
import traceback

from os import path
from random import randint

from subprocess import (
    Popen,
    PIPE,
)

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.response import FileResponse

from .report import (
    _hazardlevel_nodata,
    get_division,
    get_hazard_types,
    get_info_for_hazard_type,
    get_parents,
)

from ..models import (
    DBSession,
    AdministrativeDivision,
    HazardLevel,
    HazardCategory,
    HazardCategoryAdministrativeDivisionAssociation,
)

from sqlalchemy.orm import joinedload


logger = logging.getLogger(__name__)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.setLevel(logging.DEBUG)


@view_config(
    route_name='pdf_cover', renderer='templates/pdf_cover.jinja2')
def pdf_cover(request):
    try:
        division_code = request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')
    division = get_division(division_code)
    hazard_types = get_hazard_types(division_code)

    hazards_sorted = sorted(hazard_types, key=lambda a: a['hazardlevel'].order)

    hazard_categories = []
    for h in hazards_sorted:
        if h['hazardlevel'].mnemonic == _hazardlevel_nodata.mnemonic:
            continue
        hazard_categories.append(get_info_for_hazard_type(
            h['hazardtype'].mnemonic, division))

    context = {
        'hazards': hazard_types,
        'hazards_sorted': sorted(hazard_types,
                                 key=lambda a: a['hazardlevel'].order),
        'parents': get_parents(division),
        'division': division,
        'hazard_categories': hazard_categories,
        'date': datetime.datetime.now()
    }

    return context


@view_config(route_name='report_pdf')
def report_pdf(request):
    try:
        division_code = request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    date = datetime.datetime.now()
    filename = path.join(
        request.registry.settings.get('pdf_archive_path'),
        division_code + '-' + date.strftime('%Y-%m-%d-%H:%M:%S') +
        '-{:d}'.format(randint(1, 1E6)) + '.pdf')

    categories = DBSession.query(HazardCategory) \
        .options(joinedload(HazardCategory.hazardtype)) \
        .join(HazardCategoryAdministrativeDivisionAssociation) \
        .join(AdministrativeDivision) \
        .join(HazardLevel) \
        .filter(AdministrativeDivision.code == division_code) \
        .order_by(HazardLevel.order)

    pages = ''
    for cat in categories:
        pages = pages + ' page "{}"'.format(
            request.route_url(
                'report_print',
                divisioncode=division_code,
                hazardtype=cat.hazardtype.mnemonic
            )
        )

    cover_url = request.route_url('pdf_cover', divisioncode=division_code)

    command = \
        '.build/wkhtmltox/bin/wkhtmltopdf ' \
        '--viewport-size 800x600 --javascript-delay 2000 ' \
        'cover "%s"' \
        '%s "%s" >> /tmp/wkhtp.log' % (cover_url, pages, filename)

    try:
        p = Popen(
            command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
        stdout, stderr = p.communicate()
        retcode = p.returncode

        if retcode == 0:
            return FileResponse(
                filename,
                request=request,
                content_type='application/pdf'
            )
        elif retcode < 0:
            raise Exception("Terminated by signal: ", -retcode)
        else:
            raise Exception(stderr)

    except OSError as exc:
        logger.error(traceback.format_exc())
        raise exc
