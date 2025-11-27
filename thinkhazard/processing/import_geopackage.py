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
    """
    This script imports administrative divisions from a geopackage file.
    """

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
        LOG.info("Starting GeopackageImporter.do_execute()")
        
        if geopackage_path is None:
            LOG.error("Geopackage path is None!")
            raise ValueError("Geopackage path is required")
        
        self.geopackage_path = geopackage_path
        
        LOG.info(f"Checking if file exists: {self.geopackage_path}")
        if not os.path.isfile(self.geopackage_path):
            LOG.error(f"File not found: {self.geopackage_path}")
            raise FileNotFoundError(f"Geopackage file not found: {self.geopackage_path}")
        
        LOG.info(f"File exists! Reading geopackage file: {self.geopackage_path}")
        
        try:
            gdf = gpd.read_file(self.geopackage_path, engine="pyogrio")
            
            LOG.info(f"Successfully read geopackage file")
            LOG.info(f"Number of features: {len(gdf)}")
            LOG.info(f"Columns: {list(gdf.columns)}")
            LOG.info(f"CRS: {gdf.crs}")
            LOG.info(f"Geometry types: {gdf.geometry.geom_type.unique()}")

            LOG.info(f"Deleting temporary file: {self.geopackage_path}")
            os.unlink(self.geopackage_path)
            
            return gdf
            
        except Exception as e:
            LOG.error(f"Error reading geopackage file: {str(e)}")
            if os.path.isfile(self.geopackage_path):
                LOG.info(f"Deleting temporary file after error: {self.geopackage_path}")
                os.unlink(self.geopackage_path)
            raise
