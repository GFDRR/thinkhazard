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
import re

import os
import traceback
from uuid import uuid4

from os import path

from subprocess import (
    Popen,
    PIPE,
)

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.response import FileResponse
from thinkhazard import scheduler

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

REPORT_ID_REGEX = re.compile('\w{8}(-\w{4}){3}-\w{12}?')

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


def create_pdf(file_name, file_name_temp, cover_url, pages):
    """Create a PDF file with the given pages using wkhtmltopdf.
    wkhtmltopdf is writing the PDF in `file_name_temp`, once the generation
    has finished, the file is renamed to `file_name`.
    """
    command = path.join(
        path.dirname(__file__),
        '../../.build/wkhtmltox/bin/wkhtmltopdf')

    command += ' --viewport-size 800x600'
    command += ' --window-status "finished"'
    command += ' cover "%s"' % cover_url
    command += ' %s "%s" >> /tmp/wkhtp.log' % (pages, file_name_temp)

    try:
        p = Popen(
            command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
        stdout, stderr = p.communicate()
        retcode = p.returncode

        if retcode == 0:
            # once the generation has succeeded, rename the file so that
            # waiting clients know that it is finished
            os.rename(file_name_temp, file_name)
        elif retcode < 0:
            raise Exception("Terminated by signal: ", -retcode)
        else:
            raise Exception(stderr)

    except OSError as exc:
        logger.error(traceback.format_exc())
        raise exc
    finally:
        try:
            os.remove(file_name_temp)
        except OSError:
            pass


@view_config(
    route_name='create_pdf_report', request_method='POST', renderer='json')
def create_pdf_report(request):
    """View to create an asynchronous print job.
    """
    division_code = get_divison_code(request)

    base_path = request.registry.settings.get('pdf_archive_path')
    report_id = _get_report_id(division_code, base_path)

    categories = DBSession.query(HazardCategory) \
        .options(joinedload(HazardCategory.hazardtype)) \
        .join(HazardCategoryAdministrativeDivisionAssociation) \
        .join(AdministrativeDivision) \
        .join(HazardLevel) \
        .filter(AdministrativeDivision.code == division_code) \
        .order_by(HazardLevel.order)

    pages = ''
    for cat in categories:
        pages += ' page "{}"'.format(
            request.route_url(
                'report_print',
                divisioncode=division_code,
                hazardtype=cat.hazardtype.mnemonic
            )
        )

    cover_url = request.route_url('pdf_cover', divisioncode=division_code)

    file_name = _get_report_filename(base_path, division_code, report_id)
    file_name_temp = _get_report_filename(
        base_path, division_code, report_id, temp=True)

    # already create the file, so that the client can poll the status
    _touch(file_name_temp)

    scheduler.add_job(
        create_pdf,
        args=[file_name, file_name_temp, cover_url, pages])

    return {
        'divisioncode': division_code,
        'report_id': report_id
    }


@view_config(route_name='get_report_status', renderer='json')
def get_report_status(request):
    """View to poll the status of a print job.
    """
    division_code = get_divison_code(request)
    report_id = get_report_id(request)

    base_path = request.registry.settings.get('pdf_archive_path')
    file_name = _get_report_filename(base_path, division_code, report_id)
    file_name_temp = _get_report_filename(
        base_path, division_code, report_id, temp=True)

    if path.isfile(file_name):
        return {
            'status': 'done'
        }
    elif path.isfile(file_name_temp):
        return {
            'status': 'running'
        }
    else:
        raise HTTPNotFound('No job found or job has failed')


@view_config(route_name='get_pdf_report')
def get_pdf_report(request):
    """Return the PDF file for finished print jobs.
    """
    division_code = get_divison_code(request)
    report_id = get_report_id(request)

    base_path = request.registry.settings.get('pdf_archive_path')
    file_name = _get_report_filename(base_path, division_code, report_id)
    file_name_temp = _get_report_filename(
        base_path, division_code, report_id, temp=True)

    if path.isfile(file_name):
        return FileResponse(
            file_name,
            request=request,
            content_type='application/pdf'
        )
    elif path.isfile(file_name_temp):
        return HTTPBadRequest('Not finished yet')
    else:
        raise HTTPNotFound('No job found')


def _get_report_id(division_code, base_path):
    """Generate a random report id. Check that there is no existing file with
    the generated id.
    """
    while True:
        report_id = str(uuid4())
        file_name = _get_report_filename(
            base_path, division_code, report_id)
        file_name_temp = _get_report_filename(
            base_path, division_code, report_id, temp=True)
        if not (path.isfile(file_name) or path.isfile(file_name_temp)):
            return report_id


def _get_report_filename(base_path, division_code, report_id, temp=False):
    return path.join(
        base_path,
        ('_' if temp else '') + '{:s}-{:s}.pdf'.format(
            division_code, report_id))


def _touch(file):
    with open(file, 'a'):
        os.utime(file, None)


def get_divison_code(request):
    try:
        return request.matchdict.get('divisioncode')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')


def get_report_id(request):
    report_id = request.matchdict.get('id')
    if report_id and REPORT_ID_REGEX.match(report_id):
        return report_id
    else:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"report_id"')
