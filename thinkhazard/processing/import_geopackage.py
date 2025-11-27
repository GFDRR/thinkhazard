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
import logging
import geopandas as gpd
from thinkhazard.processing import BaseProcessor

LOG = logging.getLogger(__name__)


class GeopackageImporter(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geopackage_path = None

    @staticmethod
    def argument_parser():
        parser = BaseProcessor.argument_parser()
        parser.add_argument(
            "--geopackage-path",
            dest="geopackage_path",
            type=str,
            required=False,
            default=None,
            help="Path to the geopackage file to import",
        )
        return parser

    def do_execute(self, geopackage_path=None):
        if geopackage_path is None:
            raise ValueError("Geopackage path is required")

        self.geopackage_path = geopackage_path

        if not os.path.isfile(self.geopackage_path):
            raise FileNotFoundError(
                f"Geopackage file not found: {self.geopackage_path}"
            )

        try:
            LOG.info("Reading ADM2 source: %s", self.geopackage_path)
            gdf_adm2 = gpd.read_file(self.geopackage_path, engine="pyogrio")

            LOG.info("Extracting ADM1 boundaries...")

            adm1_cols = [
                'ISO_A3', 'ISO_A2', 'WB_A3', 'WB_REGION', 'WB_STATUS',
                'NAM_0', 'NAM_1', 'ADM1CD_c'
            ]

            hazard_score_cols = [
                'LS_Hazard_score', 'EQ_Hazard_score', 'TC_Hazard_score',
                'VO_Hazard_score', 'EH_Hazard_score', 'TS_Hazard_score',
                'WF_Hazard_score'
            ]

            aggfunc = {
                col: 'max'
                for col in hazard_score_cols
                if col in gdf_adm2.columns
            }

            gdf_adm1 = gdf_adm2.dissolve(
                by=adm1_cols, aggfunc=aggfunc, as_index=False
            )

            gdf_adm1['geometry'] = gdf_adm1.geometry.buffer(0)

            LOG.info("Extracting ADM0 boundaries...")

            adm0_cols = [
                'ISO_A3', 'ISO_A2', 'WB_A3', 'WB_REGION', 'WB_STATUS',
                'NAM_0'
            ]

            gdf_adm0 = gdf_adm2.dissolve(
                by=adm0_cols, aggfunc=aggfunc, as_index=False
            )
            gdf_adm0['geometry'] = gdf_adm0.geometry.buffer(0)

            LOG.info("Processing Complete.")
            LOG.info("ADM2 Count: %d", len(gdf_adm2))
            LOG.info("ADM1 Count: %d", len(gdf_adm1))
            LOG.info("ADM0 Count: %d", len(gdf_adm0))

            return {
                "adm2": gdf_adm2,
                "adm1": gdf_adm1,
                "adm0": gdf_adm0
            }

        except Exception as e:
            LOG.error("Error processing geopackage: %s", str(e))
            raise
