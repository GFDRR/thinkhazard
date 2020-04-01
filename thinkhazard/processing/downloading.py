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
import traceback
import os
from datetime import datetime
from urlparse import urlunsplit
import requests
import transaction

from ..models import (
    DBSession,
    Layer,
    )

from . import BaseProcessor


logger = logging.getLogger(__name__)


class Downloader(BaseProcessor):

    @staticmethod
    def argument_parser():
        parser = BaseProcessor.argument_parser()
        parser.add_argument(
            '--hazardset_id', dest='hazardset_id', action='store',
            help='The hazardset id')
        parser.add_argument(
            '-c', '--clear-cache', dest='clear_cache',
            action='store_const', const=True, default=False,
            help='Clear raster cache')
        return parser

    def clear_cache(self):
        logger.info('Clearing raster cache.')
        cache_path = os.path.join(self.settings['data_path'], 'hazardsets')
        for filename in os.listdir(cache_path):
            file_path = os.path.join(cache_path, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

    def do_execute(self, hazardset_id=None, clear_cache=False):
        if self.force or clear_cache:
            try:
                logger.info('Resetting all layers to not downloaded state.')
                DBSession.query(Layer).update({
                    Layer.downloaded: False
                })
                DBSession.flush()
            except:
                transaction.abort()
                raise

        if clear_cache:
            self.clear_cache()

        ids = DBSession.query(Layer.geonode_id)

        if not self.force:
            ids = ids.filter(Layer.downloaded.is_(False))

        if hazardset_id is not None:
            ids = ids.filter(Layer.hazardset_id == hazardset_id)

        for id in ids:
            try:
                self.download_layer(id)
                transaction.commit()
            except Exception:
                transaction.abort()
                logger.error(traceback.format_exc())

    def download_layer(self, id):
        layer = DBSession.query(Layer).get(id)
        if layer is None:
            raise Exception('Layer {} does not exist.'.format(id))

        logger.info('Downloading layer {}'.format(layer.name()))

        path = self.layer_path(layer)

        dir_path = os.path.dirname(path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # If file is obsolete, unlink
        if os.path.isfile(path):
            cache_mtime = datetime.fromtimestamp(os.path.getmtime(path))
            if layer.data_lastupdated_date > cache_mtime:
                logger.debug('  File {} considered as obsolete {} > {}'
                             .format(layer.filename(),
                                     layer.data_lastupdated_date,
                                     cache_mtime))
                os.unlink(path)
            else:
                logger.info('  File {} found in cache'
                            .format(layer.filename()))

        # If file not in cache, download it
        if not os.path.isfile(path):
            geonode = self.settings['geonode']
            url = urlunsplit((geonode['scheme'],
                              geonode['netloc'],
                              layer.download_url,
                              '',
                              ''))

            # FIXME: temporary override
            if layer.hazardset_id == 'LS-GLOBAL-arup':
                url = ("https://drive.google.com/uc?export=download"
                       "&id=1YI6OSqMruupF3CrK6UsdXQc3A4UPUtCc")

            logger.info('  Retrieving {}'.format(url))
            try:
                r = requests.get(url, stream=True)
                r.raise_for_status()
            except Exception as e:
                logger.warning('  Unable to download data for layer {}: {}'
                               .format(layer.name(),
                                       str(e)))
                return

            logger.info('  Saving to {}'.format(path))
            try:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        f.write(chunk)
            except:
                os.unlink(path)
                logger.error('Failed to save file: {}'.format(path),
                             exc_info=True)
                return False

        layer.downloaded = os.path.isfile(path)

        DBSession.flush()
