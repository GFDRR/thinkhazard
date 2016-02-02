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

import shutil
import re

from mock.mock import patch
from . import BaseTestCase


class TestReportFunction(BaseTestCase):

    def tearDown(self):  # noqa
        # delete pdf archive directory
        pdf_archive_path = self.testapp.app.registry.settings.get(
            'pdf_archive_path')
        shutil.rmtree(pdf_archive_path)
        super(TestReportFunction, self).tearDown()

    def test_report(self):
        self.testapp.get('/report/32', status=200)

    def test_report__division_desecendants(self):
        resp = self.testapp.get('/report/32', status=200)
        # 3 divisions + pin icon
        self.assertEqual(len(resp.pyquery('.breadcrumb .btn')), 4)

        resp = self.testapp.get('/report/10')
        # 1 division + pin icon
        self.assertEqual(len(resp.pyquery('.breadcrumb .btn')), 2)

    def test_report__hazardcategories(self):
        resp = self.testapp.get('/report/10', status=200)
        # admin div 10 is not linked to any hazard category
        self.assertEqual(len(resp.pyquery('.level-no-data.overview')), 8)

        resp = self.testapp.get('/report/32', status=200)
        # admin div 10 is not linked to hazard categories with one with high
        # level and one with medium level
        self.assertEqual(len(resp.pyquery('.level-HIG.overview')), 1)
        self.assertEqual(len(resp.pyquery('.level-MED.overview')), 1)

    def test_report__zoom_out(self):
        resp = self.testapp.get('/report/10')
        # no zoom out for level 1
        self.assertFalse('drillup' in resp.body)

        resp = self.testapp.get('/report/20')
        # zoom out for level > 1
        self.assertTrue('drillup' in resp.body)

    def test_report__hazard_categories(self):
        resp = self.testapp.get('/report/32')
        hazards_list = resp.pyquery('.hazard-types-list')

        # only two categories with data
        # + the one for overview
        self.assertEqual(len(hazards_list.find('li:not(.no-data)')), 3)

        hazards = hazards_list.find('li')

        # order should be 'FL', 'EQ' in icons list
        self.assertTrue('fl' in hazards.eq(1).html())
        self.assertTrue('eq' in hazards.eq(2).html())

        # whereas order should be 'EQ', 'FL' in overview list
        hazards = resp.pyquery('a.overview')
        self.assertTrue('Earthquake' in hazards.eq(0).html())
        self.assertTrue('River flood' in hazards.eq(1).html())

    def test_report__hazard(self):
        resp = self.testapp.get('/report/32/EQ', status=200)
        self.assertTrue('Climate change recommendation' in resp.body)
        self.assertEqual(len(resp.pyquery('.recommendations li')), 2)

    def test_report__further_resources(self):
        resp = self.testapp.get('/report/31/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 2)

        resp = self.testapp.get('/report/32/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 2)

    def test_report__json(self):
        self.testapp.get('/report/31/EQ.json?resolution=1000', status=200)

    def test_report__data_sources(self):
        resp = self.testapp.get('/report/31/EQ')
        print resp.body
        self.assertTrue('data_provider' in resp.body)

    @patch('thinkhazard.views.pdf.Popen')
    def test_report__pdf(self, mock):
        # tests that wkhtmltopdf is called and that the generated pdf file is
        # returned
        def popen_mock(command, **kwargs):
            pdf_file = re. \
                search('"([^"]*?32-.*?.pdf)"', command, re.IGNORECASE). \
                group(1)

            # create a dummy pdf file
            with open(pdf_file, 'w') as file:
                file.write('The pdf file')

            class PopenMock:
                def __init__(self):
                    self.returncode = 0

                def communicate(self):
                    return '', ''

            return PopenMock()
        mock.side_effect = popen_mock

        resp = self.testapp.get('/report/32.pdf', status=200)
        self.assertEqual(resp.body, 'The pdf file')
        self.assertEqual(resp.content_type, 'application/pdf')
