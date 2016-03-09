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
import os
import shutil

from mock.mock import patch
from . import BaseTestCase


class TestReportFunction(BaseTestCase):

    def setUp(self):  # noqa
        super(TestReportFunction, self).setUp()
        self.pdf_archive_path = self.testapp.app.registry.settings.get(
            'pdf_archive_path')

    def tearDown(self):  # noqa
        # delete pdf archive directory
        shutil.rmtree(self.pdf_archive_path)
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
        resp = self.testapp.get('/report/11', status=200)
        # admin div 11 is not linked to any hazard category
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

    def test_report__further_resources_division(self):
        # admin div 12 is not linked with any region => no further resource
        resp = self.testapp.get('/report/12/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 0)

        # admin div 13 is linked with global region => one single resource
        resp = self.testapp.get('/report/13/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 1)

        # admin div 10 is linked with global region and one country
        # => gets one resource for each
        resp = self.testapp.get('/report/10/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 2)

        # admin div 31 is grand child of admin div 10
        # => hence inherits the same number of further resources
        resp = self.testapp.get('/report/31/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 2)

    def test_report__json(self):
        self.testapp.get('/report/31/EQ.json?resolution=1000', status=200)

    def test_report__data_sources(self):
        resp = self.testapp.get('/report/31/EQ')
        print resp.body
        self.assertTrue('data_provider' in resp.body)

    @patch('thinkhazard.views.pdf.Popen')
    def test_create_pdf(self, mock):
        # tests that wkhtmltopdf is called and that the generated pdf file is
        # returned
        def popen_mock(command, **kwargs):
            class PopenMock:
                def __init__(self):
                    self.returncode = 0

                def communicate(self):
                    return '', ''

            return PopenMock()
        mock.side_effect = popen_mock

        pdf_file = '31-1d235e51-44d5-47ac-b6da-a96c46f21639.pdf'
        file_name = os.path.join(self.pdf_archive_path, pdf_file)
        file_name_temp = os.path.join(self.pdf_archive_path, '_' + pdf_file)
        self._touch_file('_' + pdf_file)

        from thinkhazard.views.pdf import create_pdf
        create_pdf(file_name, file_name_temp, 'cover_url', 'pages')

        self.assertTrue(os.path.isfile(file_name))

    @patch('thinkhazard.scheduler.add_job')
    def test_create_pdf_report(self, mock):
        def add_job(func, **kwargs):
            pass
        mock.side_effect = add_job

        resp = self.testapp.post('/report/create/32', status=200)
        self.assertEqual(resp.json['divisioncode'], '32')
        self.assertIsNotNone(resp.json['report_id'])

    def test_get_report_status__finished(self):
        self._touch_file('31-1d235e51-44d5-47ac-b6da-a96c46f21639.pdf')
        resp = self.testapp.get(
            '/report/status/31/1d235e51-44d5-47ac-b6da-a96c46f21639.json')
        self.assertEqual(resp.json['status'], 'done')

    def test_get_report_status__still_running(self):
        self._touch_file('_31-1d235e51-44d5-47ac-b6da-a96c46f21639.pdf')
        resp = self.testapp.get(
            '/report/status/31/1d235e51-44d5-47ac-b6da-a96c46f21639.json')
        self.assertEqual(resp.json['status'], 'running')

    def test_get_pdf_report__not_found(self):
        self.testapp.get(
            '/report/status/31/1d235e51-44d5-47ac-b6da-a96c46f21639.json',
            status=404)

    def test_get_pdf_report__found(self):
        self._touch_file('31-1d235e51-44d5-47ac-b6da-a96c46f21639.pdf')
        resp = self.testapp.get(
            '/report/31/1d235e51-44d5-47ac-b6da-a96c46f21639.pdf')
        self.assertEqual(resp.body, 'The pdf file')
        self.assertEqual(resp.content_type, 'application/pdf')

    def test_get_pdf_report__still_running(self):
        self._touch_file('_31-1d235e51-44d5-47ac-b6da-a96c46f21639.pdf')
        self.testapp.get(
            '/report/31/1d235e51-44d5-47ac-b6da-a96c46f21639.pdf', status=400)

    def test_get_pdf_report__not_found_bis(self):
        self.testapp.get(
            '/report/31/1d235e51-44d5-47ac-b6da-a96c46f21639.pdf', status=404)

    def _touch_file(self, file_name):
        with open(os.path.join(self.pdf_archive_path, file_name), 'w') as file:
            file.write('The pdf file')
