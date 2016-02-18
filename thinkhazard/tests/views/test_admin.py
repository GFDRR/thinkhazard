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

from . import BaseTestCase


class TestAdminFunction(BaseTestCase):

    def test_index(self):
        resp = self.testapp.get('/admin', status=200)
        categories = resp.html.select('.hazardcategory-link')
        self.assertEqual(len(categories), 8*4)

    def test_hazardcategory(self):
        resp = self.testapp.get('/admin/EQ/HIG', status=200)
        form = resp.form
        form['general_recommendation'] = 'Bar'
        form.submit(status=302)

    def test_technical_rec(self):
        resp = self.testapp.get('/admin/technical_rec', status=200)
        records = resp.html.select('.item-technicalrecommendation')
        self.assertEqual(len(records), 6)

    def test_technical_rec_new(self):
        resp = self.testapp.get('/admin/technical_rec/new', status=200)
        form = resp.form
        form['text'] = 'Bar'
        form['associations'] = ['EQ - MED', 'EQ - LOW']
        form.submit(status=302)

    def test_technical_rec_edit(self):
        resp = self.testapp.get('/admin/technical_rec/7', status=200)
        form = resp.form
        # here we get ['EQ - HIG'] for associations
        form['associations'] = ['EQ - MED', 'EQ - LOW']
        form.submit(status=302)
