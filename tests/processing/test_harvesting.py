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

import unittest
from datetime import datetime, timedelta
from mock import Mock, patch, mock_open
import httplib2
import json

from thinkhazard.models import FurtherResource, HazardSet, Layer, Region
from thinkhazard.processing.harvesting import Harvester

from .. import DBSession, settings
from . import BaseTestCase, populate_datamart


date_str = datetime.utcnow().isoformat()


layers_defaults = {
    "id": 1,
    "csw_type": "dataset",
    "title": "test layer",
    "data_update_date": date_str,
    "detail_url": "www.test.com",
    "download_url": "test.tif",
    "srid": "EPSG:4326",
}
layer_defaults = layers_defaults
layer_defaults.update(
    {
        "regions": [],
        "calculation_method_quality": 5,
        "hazard_period": 10,
        "hazard_unit": "m",
        "hazard_set": "TEST_GLOBAL",
        "hazard_type": "river_flood",
        "metadata_update_date": date_str,
        "owner": {"organization": ""},
        "scientific_quality": 5,
    }
)


def layers(values=[{}]):
    layers = []
    for value in values:
        layer = layers_defaults.copy()
        layer.update(value)
        layers.append(layer)
    return layers


def layer(value={}):
    layer = layer_defaults.copy()
    layer.update(value)
    if not "typename" in value:
        layer.update({
            "typename": "{}-{}".format(layer["hazard_set"], layer["hazard_period"])
        })
    return layer


@patch("thinkhazard.processing.harvesting.open", mock_open())
class TestHarvesting(BaseTestCase):

    def harvester(self):
        harvester = Harvester()
        harvester.dbsession = DBSession
        harvester.settings = settings
        return harvester

    @patch.object(Harvester, "do_execute")
    def test_cli(self, mock):
        """Test harvester cli"""
        Harvester.run(["harvest", "--config_uri", "c2c://tests.ini"])
        mock.assert_called_with(hazard_type=None, use_cache=False)

    @patch.object(Harvester, "fetch", return_value=[])
    def test_force(self, fetch_mock):
        """Test harvester in force mode"""
        harvester = self.harvester()
        harvester.force = True
        harvester.execute()

    @patch.object(
        Harvester,
        "fetch",
        return_value=[{"id": 1, "name_en": "Test region", "level": 3}],
    )
    def test_valid_region(self, fetch_mock):
        """Valid region must be added to database"""
        fetch_mock
        self.harvester().harvest_regions()
        self.assertEqual(DBSession.query(Region).count(), 2)

    @patch.object(Harvester, "fetch", return_value=layers())
    @patch.object(
        httplib2.Http, "request", return_value=(Mock(status=200), json.dumps(layer()))
    )
    def test_valid_layer(self, request_mock, fetch_mock):
        """Valid layer must be added to database"""
        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 1)

    @patch.object(
        Harvester,
        "fetch",
        return_value=[
            {"id": 1, "title": "Test document", "supplemental_information": ""}
        ],
    )
    @patch.object(
        httplib2.Http,
        "request",
        return_value=(
            Mock(status=200),
            json.dumps(
                {
                    "id": 1,
                    "csw_type": "document",
                    "hazard_type": "earthquake",
                    "regions": [],
                    "supplemental_information": "",
                    "title": "Test document",
                }
            ),
        ),
    )
    def test_valid_document(self, request_mock, fetch_mock):
        """Valid document must be added to database"""
        self.harvester().harvest_documents()
        self.assertEqual(DBSession.query(FurtherResource).count(), 1)

    @patch.object(Harvester, "fetch", return_value=layers())
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (
                Mock(status=200),
                json.dumps(
                    layer(
                        {
                            "data_update_date": (
                                datetime.utcnow() - timedelta(days=1)
                            ).isoformat()
                        }
                    )
                ),
            ),
            (
                Mock(status=200),
                json.dumps(layer({"data_update_date": datetime.utcnow().isoformat()})),
            ),
        ],
    )
    @patch("thinkhazard.processing.harvesting.os.unlink")
    def test_data_update_date_change(self, unlink_mock, request_mock, fetch_mock):
        """New data_update_date must reset hazarset.complete and processed"""
        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        hazardset.complete = True
        hazardset.processed = datetime.now()

        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete, False)
        self.assertEqual(hazardset.processed, None)
        unlink_mock.assert_called_once_with("/tmp/hazardsets/test.tif")

    @patch.object(Harvester, "fetch", return_value=layers())
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (
                Mock(status=200),
                json.dumps(
                    layer(
                        {
                            "metadata_update_date": (
                                datetime.utcnow() - timedelta(days=1)
                            ).isoformat()
                        }
                    )
                ),
            ),
            (
                Mock(status=200),
                json.dumps(
                    layer({"metadata_update_date": datetime.utcnow().isoformat()})
                ),
            ),
        ],
    )
    def test_metadata_update_date_change(self, request_mock, fetch_mock):
        """New metadata_update_date must reset hazardset.complete"""
        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        hazardset.complete = True
        hazardset.processed = datetime.now()

        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete, False)

    @patch.object(Harvester, "fetch", return_value=layers())
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (Mock(status=200), json.dumps(layer({"calculation_method_quality": 1}))),
            (Mock(status=200), json.dumps(layer({"calculation_method_quality": 2}))),
        ],
    )
    def test_calculation_method_quality_change(self, request_mock, fetch_mock):
        """New calculation_method_quality must reset hazardset.complete"""
        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        hazardset.complete = True
        hazardset.processed = datetime.now()

        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete, False)

    @patch.object(Harvester, "fetch", return_value=layers())
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (Mock(status=200), json.dumps(layer({"scientific_quality": 1}))),
            (Mock(status=200), json.dumps(layer({"scientific_quality": 2}))),
        ],
    )
    def test_scientific_quality_change(self, request_mock, fetch_mock):
        """New scientific_quality must reset hazardset.complete"""
        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        hazardset.complete = True
        hazardset.processed = datetime.now()

        self.harvester().harvest_layers()

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete, False)

    @patch.object(Harvester, "fetch", side_effect=[layers(), layers([])])
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (Mock(status=200), json.dumps(layer()))
        ]
    )
    def test_hazardset_removed(self, request_mock, fetch_mock):
        """Empty hazardsets should be removed from database"""
        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 1)
        self.assertEqual(DBSession.query(HazardSet).count(), 1)

        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 0)
        self.assertEqual(DBSession.query(HazardSet).count(), 0)

    @patch.object(Harvester, "fetch", return_value=layers())
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (Mock(status=200), json.dumps(layer({"id": 1, "hazard_period": 0})))
        ]
    )
    def test_hazardlevel_mismatch(self, request_mock, fetch_mock):
        """Layers without hazardlevel (invalid hazard_period) should not be harvested"""
        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 0)
        self.assertEqual(DBSession.query(HazardSet).count(), 0)

    @patch.object(
        Harvester,
        "fetch",
        side_effect=[
            layers([{"id": 1}, {"id": 2}]),
            layers([{"id": 1}])
        ]
    )
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (Mock(status=200), json.dumps(layer({"id": 1, "hazard_period": 10}))),
            (Mock(status=200), json.dumps(layer({"id": 2, "hazard_period": 50}))),
            (Mock(status=200), json.dumps(layer({"id": 1, "hazard_period": 10}))),
        ]
    )
    def test_layer_removed(self, request_mock, fetch_mock):
        """Layer removed from geonode should be removed from database"""
        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 2)
        self.assertEqual(DBSession.query(HazardSet).count(), 1)

        hazardset = DBSession.query(HazardSet).one()
        hazardset.completed = True
        hazardset.processed = datetime.now()
        DBSession.flush()

        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 1)
        self.assertEqual(DBSession.query(HazardSet).count(), 1)
        self.assertFalse(hazardset.completed)
        self.assertIsNone(hazardset.processed)

    @patch.object(
        Harvester,
        "fetch",
        side_effect=[
            layers([{"id": 1}, {"id": 2}]),
            layers([{"id": 1}, {"id": 2}])
        ]
    )
    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (Mock(status=200), json.dumps(layer({"id": 1, "hazard_period": 15}))),
            (Mock(status=200), json.dumps(layer({"id": 2, "hazard_period": 10}))),
            (Mock(status=200), json.dumps(layer({"id": 1, "hazard_period": 15}))),
            (Mock(status=200), json.dumps(layer({"id": 2, "hazard_period": 10}))),
        ]
    )
    def test_no_useless_process_invalidate(self, request_mock, fetch_mock):
        """Multiple layers matching same level should not invalidate processing uselessly"""
        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 1)
        self.assertEqual(DBSession.query(HazardSet).count(), 1)

        hazardset = DBSession.query(HazardSet).one()
        hazardset.completed = True
        hazardset.processed = datetime.now()
        DBSession.flush()
        DBSession.expunge_all()

        self.harvester().harvest_layers()
        self.assertEqual(DBSession.query(Layer).count(), 1)
        self.assertEqual(DBSession.query(HazardSet).count(), 1)
        self.assertTrue(hazardset.completed)
        self.assertIsNotNone(hazardset.processed)

    @patch.object(
        httplib2.Http,
        "request",
        side_effect=[
            (
                Mock(status=200),
                json.dumps(layer({"typename": "hazard:adm2_fu_raster_v3"})),
            ),
            (Mock(status=500), json.dumps({"error_message": "Some error."})),
        ],
    )
    def test_layers_api_500(self, request_mock):
        """Geonode API status 500 must not corrupt data"""
        self.harvester().harvest_layer(layers()[0])

        with self.assertRaises(Exception) as cm:
            self.harvester().harvest_layer(layers()[0])

        self.assertEqual(
            str(cm.exception),
            'Geonode returned status 500: {"error_message": "Some error."}',
        )

        layer = DBSession.query(Layer).one()
        self.assertEqual(layer.typename, "hazard:adm2_fu_raster_v3")
