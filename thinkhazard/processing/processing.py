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

import logging
import traceback
import transaction
import datetime
import rasterio
from rasterio import (
    features,
    )
from numpy import ma
from shapely.geometry import box
from geoalchemy2.shape import to_shape
from sqlalchemy import func

from ..models import (
    DBSession,
    AdministrativeDivision,
    AdminLevelType,
    HazardLevel,
    HazardSet,
    Layer,
    Output,
    )

from . import BaseProcessor


logger = logging.getLogger(__name__)


class ProcessException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class Processor(BaseProcessor):

    @staticmethod
    def argument_parser():
        parser = BaseProcessor.argument_parser()
        parser.add_argument(
            '--hazardset_id', dest='hazardset_id', action='store',
            help='The hazardset id')
        return parser

    def do_execute(self, hazardset_id):
        ids = DBSession.query(HazardSet.id) \
            .filter(HazardSet.complete.is_(True))
        if hazardset_id is not None:
            ids = ids.filter(HazardSet.id == hazardset_id)
        if not self.force:
            ids = ids.filter(HazardSet.processed.is_(None))
        if ids.count() == 0:
            logger.info('No hazardset to process')
            return
        for id in ids:
            logger.info(id[0])
            try:
                self.process_hazardset(id[0])
                transaction.commit()
            except Exception:
                transaction.abort()
                logger.error(traceback.format_exc())

    def process_hazardset(self, hazardset_id):
        hazardset = DBSession.query(HazardSet).get(hazardset_id)
        if hazardset is None:
            raise ProcessException('Hazardset {} does not exist.'
                                   .format(hazardset_id))

        chrono = datetime.datetime.now()

        if hazardset.processed is not None:
            if self.force:
                hazardset.processed = None
            else:
                raise ProcessException(
                    'Hazardset {} has already been processed.'
                    .format(hazardset.id))

        logger.info("  Cleaning previous outputs")
        DBSession.query(Output) \
            .filter(Output.hazardset_id == hazardset.id) \
            .delete()
        DBSession.flush()

        self.type_settings = self.settings['hazard_types'][
            hazardset.hazardtype.mnemonic]

        with rasterio.drivers():
            try:
                logger.info("  Opening raster files")
                # Open rasters
                self.layers = {}
                self.readers = {}
                if 'values' in self.type_settings.keys():
                    # preprocessed layer
                    layer = DBSession.query(Layer) \
                        .filter(Layer.hazardset_id == hazardset.id) \
                        .one()
                    reader = rasterio.open(self.layer_path(layer))

                    self.layers[0] = layer
                    self.readers[0] = reader

                else:
                    for level in (u'HIG', u'MED', u'LOW'):
                        hazardlevel = HazardLevel.get(level)
                        layer = DBSession.query(Layer) \
                            .filter(Layer.hazardset_id == hazardset.id) \
                            .filter(Layer.hazardlevel_id == hazardlevel.id) \
                            .one()
                        reader = rasterio.open(self.layer_path(layer))

                        self.layers[level] = layer
                        self.readers[level] = reader
                    if ('mask_return_period' in self.type_settings):
                        layer = DBSession.query(Layer) \
                            .filter(Layer.hazardset_id == hazardset.id) \
                            .filter(Layer.mask.is_(True)) \
                            .one()
                        reader = rasterio.open(self.layer_path(layer))
                        self.layers['mask'] = layer
                        self.readers['mask'] = reader

                outputs = self.create_outputs(hazardset)
                if outputs:
                    DBSession.add_all(outputs)

            finally:
                logger.info("  Closing raster files")
                for key, reader in self.readers.iteritems():
                    if reader and not reader.closed:
                        reader.close()

        hazardset.processed = datetime.datetime.now()
        DBSession.flush()

        logger.info('  Successfully processed {}, {} outputs generated in {}'
                    .format(hazardset.id,
                            len(outputs),
                            datetime.datetime.now() - chrono))

        return True

    def create_outputs(self, hazardset):
        adminlevel_reg = AdminLevelType.get(u'REG')

        self.bbox = None
        for reader in self.readers.itervalues():
            polygon = polygon_from_boundingbox(reader.bounds)
            if self.bbox is None:
                self.bbox = polygon
            else:
                self.bbox = self.bbox.intersection(polygon)

        admindivs = DBSession.query(AdministrativeDivision) \
            .filter(AdministrativeDivision.leveltype_id == adminlevel_reg.id) \
            .filter(func.ST_Intersects(AdministrativeDivision.geom,
                    func.ST_GeomFromText(self.bbox.wkt, 4326))) \
            .order_by(AdministrativeDivision.id)  # Needed by windowed querying

        current = 0
        last_percent = 0
        outputs = []
        total = admindivs.count()
        logger.info('  Iterating over {} administrative divisions'
                    .format(total))

        # Windowed querying to limit memory usage
        limit = 1000  # 1000 records <=> 10 Mo
        admindivs = admindivs.limit(limit)
        for offset in xrange(0, total, limit):
            admindivs = admindivs.offset(offset)

            for admindiv in admindivs:
                current += 1

                if admindiv.geom is None:
                    logger.warning('    {}-{} has null geometry'
                                   .format(admindiv.code, admindiv.name))
                    continue

                shape = to_shape(admindiv.geom)

                # Try block to include admindiv.code in exception message
                try:
                    if 'values' in self.type_settings.keys():
                        # preprocessed layer
                        hazardlevel = self.preprocessed_hazardlevel(shape)
                    else:
                        hazardlevel = self.notpreprocessed_hazardlevel(
                            hazardset.hazardtype.mnemonic,
                            shape)

                except Exception as e:
                    e.message = ("{}-{} raises an exception :\n{}"
                                 .format(admindiv.code,
                                         admindiv.name,
                                         e.message))
                    raise

                # Create output record
                if hazardlevel is not None:
                    output = Output()
                    output.hazardset = hazardset
                    output.admin_id = admindiv.id
                    output.hazardlevel = hazardlevel
                    outputs.append(output)

                # Remove admindiv from memory
                DBSession.expunge(admindiv)

                percent = int(100.0 * current / total)
                if percent % 10 == 0 and percent != last_percent:
                    logger.info('  ... processed {}%'.format(percent))
                    last_percent = percent

        return outputs

    def preprocessed_hazardlevel(self, geometry):
        hazardlevel = None
        reader = self.readers[0]

        for polygon in geometry.geoms:
            if not polygon.intersects(self.bbox):
                continue

            window = reader.window(*polygon.bounds)
            data = reader.read(1, window=window, masked=True)

            if data.shape[0] * data.shape[1] == 0:
                continue
            if data.mask.all():
                continue

            geometry_mask = features.geometry_mask(
                [polygon],
                out_shape=data.shape,
                transform=reader.window_transform(window),
                all_touched=True)

            data.mask = data.mask | geometry_mask
            del geometry_mask

            if data.mask.all():
                continue

            for level in (u'HIG', u'MED', u'LOW', u'VLO'):
                level_obj = HazardLevel.get(level)
                if level_obj <= hazardlevel:
                    break

                if level in self.type_settings['values']:
                    values = self.type_settings['values'][level]
                    for value in values:
                        if value in data:
                            hazardlevel = level_obj
                            break

        return hazardlevel

    def notpreprocessed_hazardlevel(self,
                                    hazardtype,
                                    geometry):
        level_vlo = HazardLevel.get(u'VLO')

        hazardlevel = None

        # Create some optimization caches
        polygons = {}
        bboxes = {}
        geometry_masks = {}  # Storage for the geometry geometry_masks

        inverted_comparison = ('inverted_comparison' in self.type_settings and
                               self.type_settings['inverted_comparison'])

        for level in (u'HIG', u'MED', u'LOW'):
            layer = self.layers[level]
            reader = self.readers[level]

            threshold = self.get_threshold(hazardtype,
                                           layer.local,
                                           layer.hazardlevel.mnemonic,
                                           layer.hazardunit)
            if threshold is None:
                raise ProcessException(
                    'No threshold found for {} {} {} {}'
                    .format(hazardtype,
                            'local' if layer.local else 'global',
                            layer.hazardlevel.mnemonic,
                            layer.hazardunit))

            for i in xrange(0, len(geometry.geoms)):
                if i not in polygons:
                    polygon = geometry.geoms[i]
                    bbox = polygon.bounds
                    polygons[i] = polygon
                    bboxes[i] = bbox
                else:
                    polygon = polygons[i]
                    bbox = bboxes[i]

                if not polygon.intersects(self.bbox):
                    continue

                window = reader.window(*bbox)

                # data: MaskedArray
                data = reader.read(1, window=window, masked=True)

                # check if data is empty (cols x rows)
                if data.shape[0] * data.shape[1] == 0:
                    continue
                # all data is masked which means that all is NODATA
                if data.mask.all():
                    continue

                if inverted_comparison:
                    data = data < threshold
                else:
                    data = data > threshold

                # some hazard types have a specific mask layer with very low
                # return period which should be used as mask for other layers
                # for example River Flood
                if ('mask_return_period' in self.type_settings):
                    mask_reader = self.readers['mask']
                    mask_window = mask_reader.window(*bbox)
                    mask = self.readers['mask'].read(1,
                                                     window=mask_window,
                                                     masked=True)
                    if inverted_comparison:
                        mask = mask < threshold
                    else:
                        mask = mask > threshold

                    # apply the specific layer mask
                    data.mask = ma.getmaskarray(data) | mask.filled(False)
                    del mask
                    if data.mask.all():
                        continue

                if i in geometry_masks:
                    geometry_mask = geometry_masks[i]
                else:
                    geometry_mask = features.geometry_mask(
                        [polygon],
                        out_shape=data.shape,
                        transform=reader.window_transform(window),
                        all_touched=True)
                    geometry_masks[i] = geometry_mask

                data.mask = ma.getmaskarray(data) | geometry_mask
                del geometry_mask

                # If at least one value is True this means that there's
                # at least one raw value > threshold
                if data.any():
                    hazardlevel = layer.hazardlevel
                    break

                # check one last time is array is filled with NODATA
                if data.mask.all():
                    continue

                # Here we have at least one value lower than the current level
                # threshold
                if hazardlevel is None:
                    hazardlevel = level_vlo

            # we got a value for the level, no need to go further, this will be
            # the highest one
            if hazardlevel == layer.hazardlevel:
                break

        return hazardlevel

    def get_threshold(self, hazardtype, local, level, unit):
        mysettings = self.settings['hazard_types'][hazardtype]['thresholds']
        while type(mysettings) is dict:
            if 'local' in mysettings.keys():
                mysettings = mysettings['local' if local else 'global']
            elif 'HIG' in mysettings.keys():
                mysettings = mysettings[level]
            elif unit in mysettings.keys():
                mysettings = mysettings[unit]
            else:
                return None
        return float(mysettings)


def polygon_from_boundingbox(boundingbox):
    return box(boundingbox[0],
               boundingbox[1],
               boundingbox[2],
               boundingbox[3])
