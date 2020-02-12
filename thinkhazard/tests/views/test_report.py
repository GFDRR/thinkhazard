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
import os
import shutil
import asyncio
from mock.mock import patch, Mock

from . import BaseTestCase

class TestReportFunction(BaseTestCase):
    def setUp(self):  # noqa
        super(TestReportFunction, self).setUp()
        self.pdf_archive_path = self.testapp.app.registry.settings.get(
            "pdf_archive_path"
        )
        if not os.path.exists(self.pdf_archive_path):
            os.makedirs(self.pdf_archive_path)
        self.report_id = "1d235e51-44d5-47ac-b6da-a96c46f21639"
        filename = "31-" + self.report_id + ".pdf"
        year = "1970"
        month = "01"
        self.pdf_file = os.path.join(self.pdf_archive_path, year, month, filename)
        self.pdf_temp_file = os.path.join(
            self.pdf_archive_path, year, month, "_" + filename
        )

    def tearDown(self):  # noqa
        # delete pdf archive directory
        shutil.rmtree(self.pdf_archive_path)
        super(TestReportFunction, self).tearDown()

    def test_report(self):
        self.testapp.get("/en/report/32-slug", status=200)

    def test_report__division_desecendants(self):
        resp = self.testapp.get("/en/report/32-slug", status=200)
        # 3 divisions + pin icon
        self.assertEqual(len(resp.pyquery(".breadcrumb .btn")), 4)

        resp = self.testapp.get("/en/report/10-slug")
        # 1 division + pin icon
        self.assertEqual(len(resp.pyquery(".breadcrumb .btn")), 2)

    def test_report__hazardcategories(self):
        resp = self.testapp.get("/en/report/11-slug", status=200)
        # admin div 11 is not linked to any hazard category
        self.assertEqual(len(resp.pyquery(".level-no-data.overview")), 12)

        resp = self.testapp.get("/en/report/32-slug", status=200)
        # admin div 10 is not linked to hazard categories with one with high
        # level and one with medium level
        self.assertEqual(len(resp.pyquery(".level-HIG.overview")), 1)
        self.assertEqual(len(resp.pyquery(".level-MED.overview")), 1)

    def test_report__zoom_out(self):
        resp = self.testapp.get("/en/report/10-slug")
        # no zoom out for level 1
        self.assertFalse("drillup" in resp.text)

        resp = self.testapp.get("/en/report/20-slug")
        # zoom out for level > 1
        self.assertTrue("drillup" in resp.text)

    def test_report__hazard_categories(self):
        resp = self.testapp.get("/en/report/32-slug")
        hazards_list = resp.pyquery(".hazard-types-list")

        # only two categories with data
        # + the one for overview
        self.assertEqual(len(hazards_list.find("li:not(.no-data)")), 3)

        hazards = hazards_list.find("li")

        # order should be 'FL', 'CF' in icons list
        self.assertTrue("fl" in hazards.eq(1).html())
        self.assertTrue("cf" in hazards.eq(3).html())

        # whereas order should be 'EQ', 'FL' in overview list
        hazards = resp.pyquery("a.overview")
        self.assertTrue("Earthquake" in hazards.eq(0).html())
        self.assertTrue("River flood" in hazards.eq(1).html())

    def test_report__hazard(self):
        resp = self.testapp.get("/en/report/32-slug/EQ", status=200)
        self.assertTrue("Climate change recommendation" in resp.text)
        self.assertEqual(len(resp.pyquery(".recommendations li")), 2)

    def test_report__further_resources_division(self):
        # admin div 12 is not linked with any region => no further resource
        resp = self.testapp.get("/en/report/12-slug/EQ", status=200)
        self.assertEqual(len(resp.pyquery(".further-resources ul li")), 0)

        # admin div 13 is linked with global region => one single resource
        resp = self.testapp.get("/en/report/13-slug/EQ", status=200)
        self.assertEqual(len(resp.pyquery(".further-resources ul li")), 1)

        # admin div 10 is linked with global region and one country
        # => gets one resource for each
        resp = self.testapp.get("/en/report/10-slug/EQ", status=200)
        self.assertEqual(len(resp.pyquery(".further-resources ul li")), 2)

        # admin div 31 is grand child of admin div 10
        # => hence inherits the same number of further resources
        resp = self.testapp.get("/en/report/31-slug/EQ", status=200)
        self.assertEqual(len(resp.pyquery(".further-resources ul li")), 2)

    def test_report__json(self):
        self.testapp.get("/en/report/31/EQ.json?resolution=1000", status=200)

    def test_report__data_sources(self):
        resp = self.testapp.get("/en/report/31-slug/EQ")
        print(resp.text)
        self.assertTrue("data_provider" in resp.text)

    def test_create_pdf_cover(self):
        self.testapp.get("/en/pdf_cover/31", status=200)

    def test_report_print(self):
        self.testapp.get("/en/report/print/31/EQ", status=200)

    def test_report__contacts(self):
        # There are two contacts for the country 10 which is parent of 32
        resp = self.testapp.get("/en/report/10-slug/EQ")
        self.assertEqual(len(resp.pyquery(".contacts ul li")), 2)

        # Division 32 is child of 10, same number of contacts
        resp = self.testapp.get("/en/report/31-slug/EQ")
        self.assertEqual(len(resp.pyquery(".contacts ul li")), 2)

        # But no contacts for River Flood
        resp = self.testapp.get("/en/report/31-slug/FL")
        self.assertEqual(len(resp.pyquery(".contacts ul li")), 0)

        # There's no contact for the country 11
        resp = self.testapp.get("/en/report/12-slug/EQ")
        self.assertEqual(len(resp.pyquery(".contacts ul li")), 0)

    @patch('thinkhazard.views.pdf.create_pdf')
    def test_create_pdf_report(self, mock):
        # thanks to https://stackoverflow.com/a/29905620
        @asyncio.coroutine
        def create(file_name, pages):
            os.makedirs(os.path.dirname(file_name))
            with open(file_name, "w") as file:
                file.write("The pdf file")

        mock.side_effect = Mock(wraps=create)
        resp = self.testapp.post("/en/report/create/32", status=200)
        self.assertEqual(resp.body.decode(), 'The pdf file')
        self.assertEqual(resp.content_type, 'application/pdf')
