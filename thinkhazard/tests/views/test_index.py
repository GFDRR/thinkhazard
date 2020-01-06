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


class TestIndexFunction(BaseTestCase):

    def test_index(self):
        resp = self.testapp.get('/en/', status=200)
        hazards = resp.html.select('.hazard-types-list .hazard-icon')
        self.assertEqual(len(hazards), 12)

    def test_index__check_lang(self):
        resp = self.testapp.get('/fr/', status=200)
        print(resp.html.findAll('html')[0]['lang'])
        self.assertEqual(resp.html.findAll('html')[0]['lang'], 'fr')

    def test_index__redirect_lang_not_available(self):
        self.testapp.get('/xx/', status=302)

    def test_index__redirect(self):
        self.testapp.get('/', status=302)
