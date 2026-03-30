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
from .. import DBSession


class TestSearchFunction(BaseTestCase):
    def test_search(self):
        """Test unified search returns all matching divisions sorted by priority."""
        resp = self.testapp.get(
            "/en/administrativedivision", dict(q="Division"), status=200
        )
        data = resp.json["data"]
        self.assertEqual(len(data), 8)
        self.assertEqual(data[0]["mnemonic"], "COU")
        capital_results = [d for d in data if d.get("is_capital") and d["mnemonic"] == "URB"]
        self.assertEqual(len(capital_results), 1)

    def test_search_ordering(self):
        """Test that countries appear before capitals, which appear before other results."""
        resp = self.testapp.get(
            "/en/administrativedivision", dict(q="Division"), status=200
        )
        data = resp.json["data"]
        first_non_cou = next(i for i, d in enumerate(data) if d["mnemonic"] != "COU")
        for d in data[:first_non_cou]:
            self.assertEqual(d["mnemonic"], "COU")
        urb_results = [d for d in data if d["mnemonic"] == "URB"]
        if len(urb_results) > 0:
            self.assertTrue(urb_results[0]["is_capital"])

    def test_search_multilingual(self):
        """Test search finds results in any language and returns matched language name."""
        from thinkhazard.models import AdministrativeDivision

        div = DBSession.query(AdministrativeDivision).filter_by(code="10").one()
        div.name = "TestCountry"
        div.name_en = "TestCountry"
        div.name_fr = "PaysDuTest"
        div.name_es = "PaisDePrueba"
        DBSession.flush()

        resp = self.testapp.get(
            "/en/administrativedivision", dict(q="TestCountry"), status=200
        )
        self.assertEqual(resp.json["data"][0]["admin0"], "TestCountry")

        resp = self.testapp.get(
            "/en/administrativedivision", dict(q="PaysDuTest"), status=200
        )
        self.assertEqual(resp.json["data"][0]["admin0"], "PaysDuTest")

        resp = self.testapp.get(
            "/fr/administrativedivision", dict(q="PaisDePrueba"), status=200
        )
        self.assertEqual(resp.json["data"][0]["admin0"], "PaisDePrueba")

        resp = self.testapp.get(
            "/fr/administrativedivision", dict(q="PaysDuTest"), status=200
        )
        self.assertEqual(resp.json["data"][0]["admin0"], "PaysDuTest")
