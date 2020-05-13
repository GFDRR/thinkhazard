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

import datetime
import logging
import re
import tempfile
import os

from typing import List

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.response import FileResponse

from io import BytesIO
from PyPDF2 import PdfFileReader, PdfFileWriter
from asyncio import run
from pyppeteer import launch

from .report import (
    _hazardlevel_nodata,
    get_division,
    get_hazard_types,
    get_info_for_hazard_type,
    get_parents,
)

from thinkhazard.models import (
    AdministrativeDivision,
    HazardLevel,
    HazardCategory,
    HazardCategoryAdministrativeDivisionAssociation,
)

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from geoalchemy2.functions import ST_Centroid

from thinkhazard.scripts.s3helper import S3Helper

REPORT_ID_REGEX = re.compile("\d{4}_\d{2}_\w{8}(-\w{4}){3}-\w{12}?")

logger = logging.getLogger(__name__)


@view_config(route_name="pdf_cover", renderer="templates/pdf_cover.jinja2")
def pdf_cover(request):
    try:
        division_code = request.matchdict.get("divisioncode")
    except:
        raise HTTPBadRequest(detail="incorrect value for parameter " '"divisioncode"')
    division = get_division(request, division_code)
    hazard_types = get_hazard_types(request, division_code)

    hazards_sorted = sorted(hazard_types, key=lambda a: a["hazardlevel"].order)

    hazard_categories = []
    for h in hazards_sorted:
        if h["hazardlevel"].mnemonic == _hazardlevel_nodata.mnemonic:
            continue
        hazard_categories.append(
            get_info_for_hazard_type(request, h["hazardtype"].mnemonic, division)
        )

    lon, lat = (
        request.dbsession.query(
            func.ST_X(ST_Centroid(AdministrativeDivision.geom)),
            func.ST_Y(ST_Centroid(AdministrativeDivision.geom)),
        )
        .filter(AdministrativeDivision.code == division_code)
        .first()
    )

    context = {
        "hazards": hazard_types,
        "hazards_sorted": sorted(hazard_types, key=lambda a: a["hazardlevel"].order),
        "parents": get_parents(division),
        "division": division,
        "division_lonlat": (lon, lat),
        "hazard_categories": hazard_categories,
        "date": datetime.datetime.now(),
    }

    return context


"""pdf_about: see index.py"""


async def create_and_upload_pdf(file_name: str, pages: List[str], object_name: str, s3_helper: S3Helper):
    """Create a PDF file with the given pages using pyppeteer.
    """
    chunks = []

    # --no-sandbox is required to make Chrome/Chromium run under root.
    browser = await launch(
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
        args=["--no-sandbox"],
    )
    page = await browser.newPage()
    for url in pages:
        await page.goto(url, {"waitUntil": "networkidle0"})
        chunks.append(
            BytesIO(await page.pdf({"format": "A4", "printBackground": True}))
        )
    await browser.close()

    # merge all pages
    writer = PdfFileWriter()
    # for page in pages:
    for chunk in chunks:
        reader = PdfFileReader(chunk)
        for index in range(reader.numPages):
            writer.addPage(reader.getPage(index))
    output = open(file_name, "wb")
    writer.write(output)
    output.close()
    s3_helper.upload_file(file_name, object_name)


@view_config(route_name="create_pdf_report", request_method="POST")
def create_pdf_report(request):
    """View to create an asynchronous print job.
    """
    publication_date = request.publication_date
    locale = request.locale_name
    division_code = request.matchdict.get("divisioncode")

    filename = "{:%Y-%m-%d}-{:s}-{:s}.pdf".format(publication_date, locale, division_code)
    s3_path = "reports/{}".format(filename)
    local_path = os.path.join(tempfile.gettempdir(), filename)

    s3_helper = _create_s3_helper(request)
    if not s3_helper.download_file(s3_path, local_path):
        categories = (
            request.dbsession.query(HazardCategory)
            .options(joinedload(HazardCategory.hazardtype))
            .join(HazardCategoryAdministrativeDivisionAssociation)
            .join(AdministrativeDivision)
            .join(HazardLevel)
            .filter(AdministrativeDivision.code == division_code)
            .order_by(HazardLevel.order)
        )
        query_args = {"_query": {"_LOCALE_": request.locale_name}}
        pages = [
            request.route_url("pdf_cover", divisioncode=division_code, **query_args),
            request.route_url("pdf_about", **query_args),
        ]
        for cat in categories:
            pages.append(
                request.route_url(
                    "report_print",
                    divisioncode=division_code,
                    hazardtype=cat.hazardtype.mnemonic,
                    **query_args,
                )
            )
        run(create_and_upload_pdf(local_path, pages, s3_path, s3_helper))

    response = FileResponse(local_path, request=request, content_type="application/pdf")
    response.headers["Content-Disposition"] = (
        'attachment; filename="ThinkHazard.pdf"'
    )
    return response


def _create_s3_helper(request):
    settings = request.registry.settings
    return S3Helper(
        settings["aws_bucket_name"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"]
    )
