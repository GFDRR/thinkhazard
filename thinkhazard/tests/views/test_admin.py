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

from . import BaseTestCase

from thinkhazard.models import (
    DBSession,
    AdminLevelType,
    AdministrativeDivision,
    ClimateChangeRecommendation,
    TechnicalRecommendation,
    )


class TestAdminFunction(BaseTestCase):

    app_name = 'admin'

    def test_index(self):
        self.testapp.get('/', status=302)

    def test_hazardcategories(self):
        resp = self.testapp.get('/hazardcategories', status=200)
        categories = resp.html.select('.hazardcategory-link')
        self.assertEqual(len(categories), 12*4)

    def test_hazardcategory(self):
        resp = self.testapp.get('/hazardcategory/EQ/HIG', status=200)
        form = resp.form
        form['general_recommendation'] = 'Bar'
        form.submit(status=302)

    def test_technical_rec(self):
        resp = self.testapp.get('/technical_rec', status=200)
        records = resp.html.select('.item-technicalrecommendation')
        self.assertEqual(len(records), 2)

    def test_technical_rec_new(self):
        resp = self.testapp.get('/technical_rec/new', status=200)
        form = resp.form
        form['text'] = 'Bar'
        form['associations'] = ['EQ - MED', 'EQ - LOW']
        form.submit(status=302)

    def test_technical_rec_edit(self):
        technical_rec = DBSession.query(TechnicalRecommendation).first()
        resp = self.testapp.get('/technical_rec/{}'
                                .format(technical_rec.id),
                                status=200)
        form = resp.form
        # here we get ['EQ - HIG'] for associations
        form['associations'] = ['EQ - MED', 'EQ - LOW']
        form.submit(status=302)

    def test_climate_rec(self):
        self.testapp.get('/climate_rec', status=302)

    def test_climate_rec_hazardtype(self):
        resp = self.testapp.get('/climate_rec/EQ', status=200)
        records = resp.html.select('.item-climatechangerecommendation')
        self.assertEqual(len(records), 2)

    def test_climate_rec_new(self):
        resp = self.testapp.get('/climate_rec/FL/new', status=200)
        form = resp.form
        form['text'] = 'Bar'
        admindivs = DBSession.query(AdministrativeDivision) \
            .join(AdminLevelType) \
            .filter(AdminLevelType.mnemonic == 'COU')
        form['associations'] = [admindiv.id for admindiv in admindivs]
        form.submit(status=302)

    def test_climate_rec_edit(self):
        climate_rec = DBSession.query(ClimateChangeRecommendation).first()
        resp = self.testapp.get('/climate_rec/{}'
                                .format(climate_rec.id),
                                status=200)
        form = resp.form
        form['text'] = 'Bar'
        admindivs = DBSession.query(AdministrativeDivision) \
            .join(AdminLevelType) \
            .filter(AdminLevelType.mnemonic == 'COU') \
            .filter(AdministrativeDivision.code == 11)
        form['associations'] = [admindiv.id for admindiv in admindivs]
        form.submit(status=302)
