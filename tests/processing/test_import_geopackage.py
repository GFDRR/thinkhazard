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

import geopandas as gpd
from unittest.mock import patch

from thinkhazard.models import (
    AdministrativeDivision,
    ClimateChangeRecommendation,
    ClimateChangeRecAdministrativeDivisionAssociation,
    Contact,
    ContactAdministrativeDivisionHazardTypeAssociation,
    HazardType,
)
from thinkhazard.processing.import_geopackage import GeopackageImporter

from .. import DBSession, engine, settings, DATA_FOLDER
from . import BaseTestCase

# ADM2_PATH = os.path.join(DATA_FOLDER, "TH_scores_ADM2_2025.gpkg")
ADM2_PATH = os.path.join(DATA_FOLDER, "ADM2.geojson")
URBAN_PATH = os.path.join(DATA_FOLDER, "URB.geojson")


# Save reference to real read_file BEFORE any patching
_real_read_file = gpd.read_file


def mock_read_file(path, layer=None, **kwargs):
    if layer == "ADM2":
        return _real_read_file(ADM2_PATH, layer=layer, engine="pyogrio")
    if layer == "URB":
        return _real_read_file(URBAN_PATH, layer=layer, engine="pyogrio")
    else:
        raise ValueError(f"Unknown layer: {layer}")


class TestGeopackageImporter(BaseTestCase):

    def importer(self):
        importer = GeopackageImporter()
        importer.engine = engine
        importer.dbsession = DBSession
        importer.settings = settings
        return importer

    @patch.object(GeopackageImporter, "do_execute")
    def test_cli(self, mock):
        """Test geopackage importer cli"""
        GeopackageImporter.run(["import_geopackage", "--config_uri", "c2c://tests.ini"])
        mock.assert_called_with(geopackage_path=None)

    @patch(
        "thinkhazard.processing.import_geopackage.gpd.read_file",
        side_effect=mock_read_file,
    )
    def test_import_adm2(self, mock_read):
        self.importer().execute(geopackage_path=ADM2_PATH, verbose=True)

    @patch(
        "thinkhazard.processing.import_geopackage.gpd.read_file",
        side_effect=mock_read_file,
    )
    def test_dry_run(self, mock_read):
        assert DBSession.query(AdministrativeDivision).count() == 3
        self.importer().execute(geopackage_path=ADM2_PATH, verbose=True, dry_run=True)
        assert DBSession.query(AdministrativeDivision).count() == 3

    @patch(
        "thinkhazard.processing.import_geopackage.gpd.read_file",
        side_effect=mock_read_file,
    )
    def test_contact_gaul(self, mock_read):
        """Test that contacts are correctly mapped using GAUL."""

        administrativedivision = AdministrativeDivision(
            code="999999",  # GAUL
            leveltype_id=1,
            name="test",
        )
        DBSession.add(administrativedivision)

        contact = Contact(
            name="test",
        )
        DBSession.add(contact)

        hazardtype = DBSession.query(HazardType).first()

        rel = ContactAdministrativeDivisionHazardTypeAssociation(
            contact=contact,
            administrativedivision=administrativedivision,
            hazardtype=hazardtype,
        )
        DBSession.add(rel)
        DBSession.flush()

        self.importer().execute(geopackage_path=ADM2_PATH, verbose=True)

        DBSession.expire_all()
        assert rel.administrativedivision.code == "TST"

    @patch(
        "thinkhazard.processing.import_geopackage.gpd.read_file",
        side_effect=mock_read_file,
    )
    def test_climatechangerecommendation_gaul(self, mock_read):
        """Test that climatechangerecommandations are correctly mapped using GAUL."""

        administrativedivision = AdministrativeDivision(
            code="999999",  # GAUL
            leveltype_id=1,
            name="test",
        )
        DBSession.add(administrativedivision)

        hazardtype = DBSession.query(HazardType).first()

        climatechangerecommendation = ClimateChangeRecommendation(
            text="test",
            hazardtype=hazardtype,
        )
        DBSession.add(climatechangerecommendation)

        rel = ClimateChangeRecAdministrativeDivisionAssociation(
            climatechangerecommendation=climatechangerecommendation,
            administrativedivision=administrativedivision,
            hazardtype=hazardtype,
        )
        DBSession.add(rel)
        DBSession.flush()

        self.importer().execute(geopackage_path=ADM2_PATH, verbose=True)

        DBSession.expire_all()
        assert rel.administrativedivision.code == "TST"
