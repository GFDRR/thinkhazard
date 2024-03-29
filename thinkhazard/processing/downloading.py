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

import logging
import os
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
import requests

from thinkhazard.models import Layer
from thinkhazard.processing import BaseProcessor


logger = logging.getLogger(__name__)


class Downloader(BaseProcessor):
    @staticmethod
    def argument_parser():
        parser = BaseProcessor.argument_parser()
        parser.add_argument(
            "--hazardset_id",
            dest="hazardset_id",
            action="store",
            help="The hazardset id",
        )
        parser.add_argument(
            "-c",
            "--clear-cache",
            dest="clear_cache",
            action="store_const",
            const=True,
            default=False,
            help="Clear raster cache",
        )
        return parser

    def clear_cache(self):
        logger.info("Clearing raster cache.")
        cache_path = os.path.join(self.settings["data_path"], "hazardsets")
        for filename in os.listdir(cache_path):
            file_path = os.path.join(cache_path, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    def do_execute(self, hazardset_id=None, clear_cache=False):
        # Layer.downloaded field is not reliable in docker context
        self.force = True

        if self.force or clear_cache:
            try:
                with self.dbsession.begin_nested():
                    logger.info("Resetting all layers to not downloaded state.")
                    self.dbsession.query(Layer).update({Layer.downloaded: False})
                    self.dbsession.flush()
            except:
                raise

        if clear_cache:
            self.clear_cache()

        ids = self.dbsession.query(Layer.geonode_id)

        if not self.force:
            ids = ids.filter(Layer.downloaded.is_(False))

        if hazardset_id is not None:
            ids = ids.filter(Layer.hazardset_id == hazardset_id)

        for id in ids:
            with self.dbsession.begin_nested():
                self.download_layer(id)

    def download_layer(self, id):
        layer = self.dbsession.query(Layer).get(id)
        if layer is None:
            raise Exception("Layer {} does not exist.".format(id))

        logger.info("Downloading layer {}".format(layer.name()))

        path = self.layer_path(layer)

        dir_path = os.path.dirname(path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # If file is obsolete, unlink
        if os.path.isfile(path):
            cache_mtime = datetime.fromtimestamp(os.path.getmtime(path))
            if layer.data_lastupdated_date > cache_mtime:
                logger.debug(
                    "  File {} considered as obsolete {} > {}".format(
                        layer.filename(), layer.data_lastupdated_date, cache_mtime
                    )
                )
                os.unlink(path)
            else:
                logger.info("  File {} found in cache".format(layer.filename()))

        # If file not in cache, download it
        if not os.path.isfile(path):
            geonode = self.settings["geonode"]
            parsed = urlsplit(geonode["url"])
            url = urlunsplit(
                (parsed.scheme, parsed.netloc, layer.download_url, "", "")
            )

            # FIXME: temporary override
            if layer.hazardset_id == "LS-GLOBAL-arup":
                url = ("https://drive.google.com/uc?export=download"
                       "&id=18ilYOnMikhBZ708uole4jpeghRd4soD7")

            # FIXME: temporary override
            if layer.hazardset_id == "FL-GLOBAL-FATHOM":
                url = urlunsplit(
                    (parsed.scheme, parsed.netloc, "/uploaded/layers/adm2_fu_v3_4bit.tif", "", "")
                )

            logger.info("  Retrieving {}".format(url))
            try:
                r = requests.get(url, stream=True)
                r.raise_for_status()
            except Exception as e:
                logger.warning(
                    "  Unable to download data for layer {}: {}".format(
                        layer.name(), str(e)
                    )
                )
                return

            logger.info("  Saving to {}".format(path))
            try:
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        f.write(chunk)
            except:
                os.unlink(path)
                logger.error("Failed to save file: {}".format(path), exc_info=True)
                return False

        layer.downloaded = os.path.isfile(path)

        self.dbsession.flush()
