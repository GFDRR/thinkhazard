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

import asyncio
import datetime
import logging
import re
import tempfile
import os

from typing import List

import httpx
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.response import FileResponse

from io import BytesIO
from PyPDF2 import PdfFileReader, PdfFileWriter
from asyncio import run

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

REPORT_ID_REGEX = re.compile(r"\d{4}_\d{2}_\w{8}(-\w{4}){3}-\w{12}?")

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


async def create_and_upload_pdf(request, file_name: str, pages: List[str], object_name: str):
    """Create a PDF file with the given pages using pyppeteer.
    """
    async def render_page(page):
        puppeteer_url = request.registry.settings["puppeteer_url"]

        timeout = httpx.Timeout(
            connect=30.0,
            read=60.0,
            write=30.0,
            pool=30.0
        )

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            try:
                logger.info("Starting PDF generation for PAGE: %s", page)
                r = await client.get(f"{puppeteer_url}/generate-pdf", params={"path": page})
                logger.info("PDF generation completed for PAGE: %s", page)
                r.raise_for_status()
                return BytesIO(r.content)
            except Exception as e:
                logger.error("Error when requesting PAGE: %s - %s", page, str(e))
                raise

        return BytesIO(r.content)

    chunks = await asyncio.gather(*[
        render_page(page) for page in pages
    ])

    # merge all pages
    writer = PdfFileWriter()
    # for page in pages:
    for chunk in chunks:
        reader = PdfFileReader(chunk)
        for index in range(reader.numPages):
            writer.addPage(reader.getPage(index))

    with open(file_name, "wb") as output:
        writer.write(output)

    request.s3_helper.upload_file(file_name, object_name)


@view_config(route_name="create_pdf_report")
def create_pdf_report(request):
    """View to create an asynchronous print job.
    """
    publication_date = request.publication_date
    locale = request.locale_name
    division_code = request.matchdict.get("divisioncode")
    force = "force" in request.params

    filename = "{:s}-{:s}.pdf".format(division_code, locale)
    s3_path = "reports/{:%Y-%m-%d}/{}".format(publication_date, filename)
    local_path = os.path.join(tempfile.gettempdir(), filename)

    if force or not request.s3_helper.download_file(s3_path, local_path):
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
            request.route_path("pdf_cover", divisioncode=division_code, **query_args),
            request.route_path("pdf_about", **query_args),
        ]
        for cat in categories:
            pages.append(
                request.route_path(
                    "report_print",
                    divisioncode=division_code,
                    hazardtype=cat.hazardtype.mnemonic,
                    **query_args,
                )
            )
        run(create_and_upload_pdf(request, local_path, pages, s3_path))

    response = FileResponse(local_path, request=request, content_type="application/pdf")
    response.headers["Content-Disposition"] = (
        'attachment; filename="ThinkHazard.pdf"'
    )
    return response
