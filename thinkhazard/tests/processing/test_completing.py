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
import transaction
from datetime import datetime
from mock import Mock, patch
from rasterio._io import RasterReader
from rasterio.coords import BoundingBox
from affine import Affine

from ...models import (
    DBSession,
    HazardLevel,
    HazardSet,
    HazardType,
    Layer,
    Region,
    )

from .. import settings
from . import populate_datamart
from .common import new_geonode_id
from ...processing.completing import Completer


def populate():
    DBSession.query(Layer).delete()
    DBSession.query(HazardSet).delete()
    populate_datamart()
    transaction.commit()


def global_reader(path=''):
    reader = Mock(spec=RasterReader)
    reader.shape = (360, 720)
    reader.affine = Affine(-180., 0.5, 0.0, -90., 0.0, 0.5)
    reader.bounds = BoundingBox(-180., -90., 0., 0.)

    context = Mock()
    context.__enter__ = Mock(return_value=reader)
    context.__exit__ = Mock(return_value=False)
    return context


def global_reader_bis(path=''):
    reader = Mock(spec=RasterReader)
    reader.shape = (361, 720)
    reader.affine = Affine(-180., 0.5, 0.0, -90., 0.0, 0.5)
    reader.bounds = BoundingBox(-180., -90., 0.5, 0.)

    context = Mock()
    context.__enter__ = Mock(return_value=reader)
    context.__exit__ = Mock(return_value=False)
    return context


def global_reader_invalid_bounds(path=''):
    reader = Mock(spec=RasterReader)
    reader.shape = (360, 720)
    reader.affine = Affine(-180., 0.5, 0.0, 90., 0.0, -0.5)
    reader.bounds = BoundingBox(-180., 90., 0.5, 0.)

    context = Mock()
    context.__enter__ = Mock(return_value=reader)
    context.__exit__ = Mock(return_value=False)
    return context


class TestCompleting(unittest.TestCase):

    def setUp(self):  # NOQA
        populate()

    @patch.object(Completer, 'do_execute')
    def test_cli(self, mock):
        '''Test completer cli'''
        Completer.run(['complete', '--config_uri', 'tests.ini'])
        mock.assert_called_with(hazardset_id=None)

    def test_force(self):
        '''Test completer in force mode'''
        Completer().execute(settings, force=True)

    @patch('rasterio.open', side_effect=global_reader)
    def test_complete_preprocessed(self, open_mock):
        '''Test complete preprocessed hazardset'''

        hazardset_id = 'preprocessed'
        hazardtype = HazardType.get('VA')

        regions = DBSession.query(Region).all()

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            regions=regions)
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

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete_error, None)
        self.assertEqual(hazardset.complete, True)

    @patch('rasterio.open', side_effect=global_reader)
    def test_complete_notpreprocessed(self, open_mock):
        '''Test complete notpreprocessed hazardset'''

        hazardset_id = 'notpreprocessed'
        hazardtype = HazardType.get('EQ')

        regions = DBSession.query(Region).all()

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            regions=regions)
        DBSession.add(hazardset)

        for level in ['HIG', 'MED', 'LOW']:
            layer = Layer(
                hazardlevel=HazardLevel.get(level),
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

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete_error, None)
        self.assertEqual(hazardset.complete, True)

    def test_no_region(self):
        '''Test no region'''

        hazardset_id = 'notpreprocessed'
        hazardtype = HazardType.get('EQ')

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now())
        DBSession.add(hazardset)

        for level in ['HIG', 'MED', 'LOW']:
            layer = Layer(
                hazardlevel=HazardLevel.get(level),
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

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete_error, 'No associated regions')
        self.assertEqual(hazardset.complete, False)

    @patch('rasterio.open', side_effect=global_reader_invalid_bounds)
    def test_invalid_bounds(self, open_mock):
        '''Test invalid invalid'''

        hazardset_id = 'notpreprocessed'
        hazardtype = HazardType.get('EQ')

        regions = DBSession.query(Region).all()

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            regions=regions)
        DBSession.add(hazardset)

        for level in ['HIG', 'MED', 'LOW']:
            layer = Layer(
                hazardlevel=HazardLevel.get(level),
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

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete_error,
                         'bounds.bottom > bounds.top')
        self.assertEqual(hazardset.complete, False)

    @patch('rasterio.open', side_effect=global_reader)
    def test_missing_level(self, open_mock):
        '''Test missing level'''

        hazardset_id = 'notpreprocessed'
        hazardtype = HazardType.get('EQ')

        regions = DBSession.query(Region).all()

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            regions=regions)
        DBSession.add(hazardset)

        for level in ['HIG', 'MED']:
            layer = Layer(
                hazardlevel=HazardLevel.get(level),
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

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete_error, 'No layer for level LOW')
        self.assertEqual(hazardset.complete, False)

    @patch('rasterio.open', side_effect=global_reader)
    def test_missing_mask(self, open_mock):
        '''Test missing mask'''

        hazardset_id = 'notpreprocessed'
        hazardtype = HazardType.get('FL')

        regions = DBSession.query(Region).all()

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            regions=regions)
        DBSession.add(hazardset)

        for level in ['HIG', 'MED', 'LOW']:
            layer = Layer(
                hazardlevel=HazardLevel.get(level),
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

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete_error, 'Missing mask layer')
        self.assertEqual(hazardset.complete, False)

    @patch('rasterio.open', side_effect=Exception())
    def test_open_exception(self, open_mock):
        '''Test handling of open exception'''

        hazardset_id = 'notpreprocessed'
        hazardtype = HazardType.get('EQ')

        regions = DBSession.query(Region).all()

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            regions=regions)
        DBSession.add(hazardset)

        for level in ['HIG', 'MED', 'LOW']:
            layer = Layer(
                hazardlevel=HazardLevel.get(level),
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

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(hazardset.complete_error,
                         "Error opening layer notpreprocessed")
        self.assertEqual(hazardset.complete, False)

    @patch('rasterio.open', side_effect=[
        global_reader(),
        global_reader(),
        global_reader(),
        global_reader_bis()])
    def test_not_corresponding_rasters(self, open_mock):
        '''Difference in origin, resolution or size must not complete'''

        hazardset_id = 'notpreprocessed'
        hazardtype = HazardType.get('FL')

        regions = DBSession.query(Region).all()

        hazardset = HazardSet(
            id=hazardset_id,
            hazardtype=hazardtype,
            local=False,
            data_lastupdated_date=datetime.now(),
            metadata_lastupdated_date=datetime.now(),
            regions=regions)
        DBSession.add(hazardset)

        for level in ['HIG', 'MED', 'LOW']:
            layer = Layer(
                hazardlevel=HazardLevel.get(level),
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

        mask_layer = Layer(
            hazardlevel=None,
            mask=True,
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
        hazardset.layers.append(mask_layer)

        transaction.commit()

        Completer().execute(settings)

        hazardset = DBSession.query(HazardSet).one()
        self.assertEqual(
            hazardset.complete_error,
            'All layers should have the same origin, resolution and size')
        self.assertEqual(hazardset.complete, False)
