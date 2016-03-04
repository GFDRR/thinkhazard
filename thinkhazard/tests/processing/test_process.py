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

import unittest
import transaction
from datetime import datetime
from shapely.geometry import (
    MultiPolygon,
    Polygon,
    )
from geoalchemy2.shape import from_shape
import numpy as np
from mock import Mock, patch
from rasterio._io import RasterReader
from affine import Affine

from ...models import (
    DBSession,
    AdminLevelType,
    AdministrativeDivision,
    HazardLevel,
    HazardSet,
    HazardType,
    Layer,
    Output,
    )

from ...processing import settings
from ...processing.processing import Processor
from common import new_geonode_id


preprocessed_type = u'VA'
notpreprocessed_type = u'FL'
notpreprocessed_unit = 'm'


def populate():
    DBSession.query(Output).delete()
    DBSession.query(Layer).delete()
    DBSession.query(HazardSet).delete()
    DBSession.query(AdministrativeDivision).delete()
    populate_datamart()
    populate_notpreprocessed(notpreprocessed_type, notpreprocessed_unit)
    populate_preprocessed(preprocessed_type)
    transaction.commit()


def global_reader(value=None):
    array = np.ma.masked_array(
        np.empty(shape=(360, 720), dtype=np.float32, order='C'),
        np.empty(shape=(360, 720), dtype=np.bool, order='C'))
    if value is None:
        array.mask.fill(True)
    else:
        array.fill(value)
        array.mask.fill(False)
    transform = Affine(-180., 0.5, 0.0, 90., 0.0, -0.5)
    reader = Mock(spec=RasterReader)
    reader.read.return_value = array
    reader.shape = array.shape
    reader.transform = transform
    reader.bounds = (-180., -90., 180., 90.)
    reader.window.return_value = ((0, 359), (0, 719))
    reader.window_transform.return_value = transform
    return reader


class TestProcess(unittest.TestCase):

    def setUp(self):  # NOQA
        populate()

    @patch('rasterio.open')
    def test_process_empty(self, open_mock):
        '''Test nodata everywhere'''
        open_mock.side_effect = [
            global_reader(),
            global_reader(),
            global_reader(),
            global_reader()
        ]
        Processor().execute(hazardset_id='notpreprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output, None)

    @patch('rasterio.open')
    def test_process_vlo(self, open_mock):
        '''Test value < threshold <=> hazardlevel VLO'''
        open_mock.side_effect = [
            global_reader(0.0),
            global_reader(),
            global_reader(),
            global_reader()
        ]
        Processor().execute(hazardset_id='notpreprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, 'VLO')

    @patch('rasterio.open')
    def test_process_low(self, open_mock):
        '''Test value > threshold in LOW layer'''
        open_mock.side_effect = [
            global_reader(),
            global_reader(),
            global_reader(100.0),
            global_reader(),
        ]
        Processor().execute(hazardset_id='notpreprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, u'LOW')

    @patch('rasterio.open')
    def test_process_med(self, open_mock):
        '''Test value > threshold in MED layer'''
        open_mock.side_effect = [
            global_reader(),
            global_reader(100.0),
            global_reader(),
            global_reader(),
        ]
        Processor().execute(hazardset_id='notpreprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, u'MED')

    @patch('rasterio.open')
    def test_process_hig(self, open_mock):
        '''Test value > threshold in HIG layer'''
        open_mock.side_effect = [
            global_reader(100.0),
            global_reader(),
            global_reader(),
            global_reader()
        ]
        Processor().execute(hazardset_id='notpreprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, u'HIG')

    @patch('rasterio.open')
    def test_process_mask(self, open_mock):
        '''Test mask layer'''
        open_mock.side_effect = [
            global_reader(100.0),
            global_reader(),
            global_reader(),
            global_reader(100.0)
        ]
        Processor().execute(hazardset_id='notpreprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output, None)

    @patch('rasterio.open')
    def test_preprocessed_empty(self, open_mock):
        '''Test mask layer'''
        open_mock.side_effect = [
            global_reader(),
        ]
        Processor().execute(hazardset_id='preprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output, None)

    @patch('rasterio.open')
    def test_preprocessed_vlo(self, open_mock):
        '''Test mask layer'''
        hazardtype = HazardType.get(preprocessed_type)
        hazardtype_settings = settings['hazard_types'][hazardtype.mnemonic]
        open_mock.side_effect = [
            global_reader(hazardtype_settings['values']['VLO'][0]),
        ]
        Processor().execute(hazardset_id='preprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, u'VLO')

    @patch('rasterio.open')
    def test_preprocessed_low(self, open_mock):
        '''Test mask layer'''
        hazardtype = HazardType.get(preprocessed_type)
        hazardtype_settings = settings['hazard_types'][hazardtype.mnemonic]
        open_mock.side_effect = [
            global_reader(hazardtype_settings['values']['VLO'][0]),
        ]
        Processor().execute(hazardset_id='preprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, u'VLO')

    @patch('rasterio.open')
    def test_preprocessed_med(self, open_mock):
        '''Test mask layer'''
        hazardtype = HazardType.get(preprocessed_type)
        hazardtype_settings = settings['hazard_types'][hazardtype.mnemonic]
        open_mock.side_effect = [
            global_reader(hazardtype_settings['values']['MED'][0]),
        ]
        Processor().execute(hazardset_id='preprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, u'MED')

    @patch('rasterio.open')
    def test_preprocessed_hig(self, open_mock):
        '''Test mask layer'''
        hazardtype = HazardType.get(preprocessed_type)
        hazardtype_settings = settings['hazard_types'][hazardtype.mnemonic]
        open_mock.side_effect = [
            global_reader(hazardtype_settings['values']['HIG'][0]),
        ]
        Processor().execute(hazardset_id='preprocessed')
        output = DBSession.query(Output).first()
        self.assertEqual(output.hazardlevel.mnemonic, u'HIG')


def populate_datamart():
    print 'populate datamart'
    adminlevel_reg = AdminLevelType.get(u'REG')

    shape = MultiPolygon([
        Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    ])
    geometry = from_shape(shape, 4326)

    div = AdministrativeDivision(**{
        'code': 30,
        'leveltype_id': adminlevel_reg.id,
        'name': u'Administrative division level 3'
    })
    div.geom = geometry
    div.hazardcategories = []
    DBSession.add(div)

    DBSession.flush()


def populate_notpreprocessed(type, unit):
    hazardset_id = u'notpreprocessed'
    hazardtype = HazardType.get(type)
    hazardtype_settings = settings['hazard_types'][hazardtype.mnemonic]

    print 'Populating hazardset {}'.format(hazardset_id)
    hazardset = HazardSet(
        id=hazardset_id,
        hazardtype=hazardtype,
        local=False,
        data_lastupdated_date=datetime.now(),
        metadata_lastupdated_date=datetime.now())
    DBSession.add(hazardset)

    return_periods = hazardtype_settings['return_periods']

    for level in (u'HIG', u'MED', u'LOW'):
        hazardlevel = HazardLevel.get(level)
        level_return_periods = return_periods[level]
        if isinstance(level_return_periods, list):
            return_period = level_return_periods[0]
        else:
            return_period = level_return_periods

        layer = Layer(
            hazardlevel=hazardlevel,
            mask=False,
            return_period=return_period,
            hazardunit=unit,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            geonode_id=new_geonode_id(),
            download_url='test',
            calculation_method_quality=5,
            scientific_quality=1,
            local=False,
            downloaded=True
        )
        hazardset.layers.append(layer)

    layer = Layer(
        hazardlevel=None,
        mask=True,
        return_period=hazardtype_settings['mask_return_period'],
        hazardunit=unit,
        data_lastupdated_date=datetime.now(),
        metadata_lastupdated_date=datetime.now(),
        geonode_id=new_geonode_id(),
        download_url='test',
        calculation_method_quality=5,
        scientific_quality=1,
        local=False,
        downloaded=True
    )
    hazardset.layers.append(layer)

    hazardset.complete = True
    DBSession.flush()


def populate_preprocessed(type):
    hazardset_id = u'preprocessed'
    hazardtype = HazardType.get(type)

    print 'Populating hazardset {}'.format(hazardset_id)
    hazardset = HazardSet(
        id=hazardset_id,
        hazardtype=hazardtype,
        local=False,
        data_lastupdated_date=datetime.now(),
        metadata_lastupdated_date=datetime.now())
    DBSession.add(hazardset)

    layer = Layer(
        hazardlevel=None,
        mask=False,
        return_period=None,
        data_lastupdated_date=datetime.now(),
        metadata_lastupdated_date=datetime.now(),
        geonode_id=new_geonode_id(),
        download_url='test',
        calculation_method_quality=5,
        scientific_quality=1,
        local=False,
        downloaded=True
    )
    hazardset.layers.append(layer)

    hazardset.complete = True
    DBSession.flush()
