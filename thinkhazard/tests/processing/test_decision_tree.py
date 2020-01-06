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
from shapely.geometry import Polygon
from geoalchemy2.shape import from_shape

from ...models import (
    DBSession,
    AdministrativeDivision,
    HazardLevel,
    HazardSet,
    HazardType,
    Layer,
    Output,
    )

from .common import new_geonode_id


def populate():
    DBSession.query(Output).delete()
    DBSession.query(AdministrativeDivision).delete()
    DBSession.query(Layer).delete()
    DBSession.query(HazardSet).delete()
    populate_datamart()
    populate_processing()
    transaction.commit()


# make dumb layers for hazardsets
def make_layers():
    layers = []
    for level in ('HIG', 'MED', 'LOW'):
        layer = Layer()
        layer.hazardlevel = HazardLevel.get(level)
        layer.return_period = 1
        layer.hazardunit = 'm'
        layer.data_lastupdated_date = datetime.now()
        layer.metadata_lastupdated_date = datetime.now()
        layer.geonode_id = new_geonode_id()
        layer.download_url = 'http://something'
        layer.calculation_method_quality = 5
        layer.scientific_quality = 1
        layer.local = False
        layer.downloaded = True
        layers.append(layer)
    return layers


def populate_datamart():
    shape = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    geometry = from_shape(shape, 3857)

    div_level_1 = AdministrativeDivision(**{
        'code': 10,
        'leveltype_id': 1,
        'name': 'Division level 1'
    })
    div_level_1.geom = geometry
    DBSession.add(div_level_1)

    div_level_2 = AdministrativeDivision(**{
        'code': 20,
        'leveltype_id': 2,
        'name': 'Division level 2'
    })
    div_level_2.parent_code = div_level_1.code
    div_level_2.geom = geometry
    DBSession.add(div_level_2)

    div_level_3_0 = AdministrativeDivision(**{
        'code': 30,
        'leveltype_id': 3,
        'name': 'Division level 3 - 1'
    })
    div_level_3_0.parent_code = div_level_2.code
    div_level_3_0.geom = geometry
    div_level_3_0.hazardcategories = []
    DBSession.add(div_level_3_0)

    div_level_3_1 = AdministrativeDivision(**{
        'code': 31,
        'leveltype_id': 3,
        'name': 'Division level 3 - 1'
    })
    div_level_3_1.parent_code = div_level_2.code
    div_level_3_1.geom = geometry
    div_level_3_1.hazardcategories = []
    DBSession.add(div_level_3_1)

    div_level_3_2 = AdministrativeDivision(**{
        'code': 32,
        'leveltype_id': 3,
        'name': 'Division level 3 - 2'
    })
    div_level_3_2.parent_code = div_level_2.code
    div_level_3_2.geom = geometry
    div_level_3_2.hazardcategories = []
    DBSession.add(div_level_3_2)

    div_level_3_3 = AdministrativeDivision(**{
        'code': 33,
        'leveltype_id': 3,
        'name': 'Division level 3 - 3'
    })
    div_level_3_3.parent_code = div_level_2.code
    div_level_3_3.geom = geometry
    div_level_3_3.hazardcategories = []
    DBSession.add(div_level_3_3)

    div_level_3_4 = AdministrativeDivision(**{
        'code': 34,
        'leveltype_id': 3,
        'name': 'Division level 3 - 4'
    })
    div_level_3_4.parent_code = div_level_2.code
    div_level_3_4.geom = geometry
    div_level_3_4.hazardcategories = []
    DBSession.add(div_level_3_4)

    div_level_3_5 = AdministrativeDivision(**{
        'code': 35,
        'leveltype_id': 3,
        'name': 'Division level 3 - 5'
    })
    div_level_3_5.parent_code = div_level_2.code
    div_level_3_5.geom = geometry
    div_level_3_5.hazardcategories = []
    DBSession.add(div_level_3_5)

    div_level_3_6 = AdministrativeDivision(**{
        'code': 36,
        'leveltype_id': 3,
        'name': 'Division level 3 - 6'
    })
    div_level_3_6.parent_code = div_level_2.code
    div_level_3_6.geom = geometry
    div_level_3_6.hazardcategories = []
    DBSession.add(div_level_3_6)

    DBSession.flush()


def populate_processing():
    hazardtype_eq = HazardType.get('EQ')
    hazardtype_fl = HazardType.get('FL')

    hazardset_id = 'hazardset1'
    print('Populating hazardset {}'.format(hazardset_id))
    hazardset1 = HazardSet()
    hazardset1.id = hazardset_id
    hazardset1.hazardtype = hazardtype_eq
    hazardset1.local = False
    hazardset1.calculation_method_quality = 0
    hazardset1.data_lastupdated_date = datetime.now()
    hazardset1.metadata_lastupdated_date = datetime.now()
    hazardset1.complete = True
    hazardset1.layers.extend(make_layers())
    DBSession.add(hazardset1)

    hazardset_id = 'hazardset1b'
    print('Populating hazardset {}'.format(hazardset_id))
    hazardset1b = HazardSet()
    hazardset1b.id = hazardset_id
    hazardset1b.hazardtype = hazardtype_fl
    hazardset1b.local = True
    hazardset1b.calculation_method_quality = 3
    hazardset1b.data_lastupdated_date = datetime.now()
    hazardset1b.metadata_lastupdated_date = datetime.now()
    hazardset1b.complete = True
    hazardset1b.layers.extend(make_layers())
    DBSession.add(hazardset1b)

    # create hazardsets 2, 3 ... 5
    hazardset_id = 'hazardset2'
    # calculation_method_quality = 1 / scientific_quality = 0
    print('Populating hazardset {}'.format(hazardset_id))
    hazardset2 = HazardSet()
    hazardset2.id = hazardset_id
    hazardset2.hazardtype = hazardtype_eq
    hazardset2.local = True
    hazardset2.calculation_method_quality = 1
    hazardset2.scientific_quality = 0
    hazardset2.data_lastupdated_date = datetime.now()
    hazardset2.metadata_lastupdated_date = datetime.now()
    hazardset2.complete = True
    hazardset2.layers.extend(make_layers())
    DBSession.add(hazardset2)

    hazardset_id = 'hazardset3'
    # date = 2015-01-01 / global /
    # calculation_method_quality = 1 / scientific_quality = 2
    print('Populating hazardset {}'.format(hazardset_id))
    hazardset3 = HazardSet()
    hazardset3.id = hazardset_id
    hazardset3.hazardtype = hazardtype_eq
    hazardset3.local = False
    hazardset3.calculation_method_quality = 1
    hazardset3.scientific_quality = 2
    hazardset3.data_lastupdated_date = datetime(2015, 1, 1, 0, 0)
    hazardset3.metadata_lastupdated_date = datetime.now()
    hazardset3.complete = True
    hazardset3.layers.extend(make_layers())
    DBSession.add(hazardset3)

    hazardset_id = 'hazardset4'
    # date = 2015-01-01 / local /
    # calculation_method_quality = 1 / scientific_quality = 2
    print('Populating hazardset {}'.format(hazardset_id))
    hazardset4 = HazardSet()
    hazardset4.id = hazardset_id
    hazardset4.hazardtype = hazardtype_eq
    hazardset4.local = True
    hazardset4.calculation_method_quality = 1
    hazardset4.scientific_quality = 2
    hazardset4.data_lastupdated_date = datetime(2015, 1, 1, 0, 0)
    hazardset4.metadata_lastupdated_date = datetime.now()
    hazardset4.complete = True
    hazardset4.layers.extend(make_layers())
    DBSession.add(hazardset4)

    hazardset_id = 'hazardset5'
    # date = now() / local /
    # calculation_method_quality = 1 / scientific_quality = 2
    print('Populating hazardset {}'.format(hazardset_id))
    hazardset5 = HazardSet()
    hazardset5.id = hazardset_id
    hazardset5.hazardtype = hazardtype_eq
    hazardset5.local = True
    hazardset5.calculation_method_quality = 1
    hazardset5.scientific_quality = 2
    hazardset5.data_lastupdated_date = datetime.now()
    hazardset5.metadata_lastupdated_date = datetime.now()
    hazardset5.complete = True
    hazardset5.layers.extend(make_layers())
    DBSession.add(hazardset5)

    hazardset_id = 'hazardset6'
    # date = now() / global /
    # calculation_method_quality = 1 / scientific_quality = 2
    print('Populating hazardset {}'.format(hazardset_id))
    hazardset6 = HazardSet()
    hazardset6.id = hazardset_id
    hazardset6.hazardtype = hazardtype_eq
    hazardset6.local = False
    hazardset6.calculation_method_quality = 1
    hazardset6.scientific_quality = 2
    hazardset6.data_lastupdated_date = datetime.now()
    hazardset6.metadata_lastupdated_date = datetime.now()
    hazardset6.complete = True
    hazardset6.layers.extend(make_layers())
    DBSession.add(hazardset6)

    # populate output table

    # admin div (code 30) has only one hazardset for EQ
    admin30 = DBSession.query(AdministrativeDivision)\
        .filter(AdministrativeDivision.code == 30).one()
    # => test outcome = hazardset1
    output1 = Output()
    output1.hazardset = hazardset1
    output1.administrativedivision = admin30
    output1.hazardlevel = HazardLevel.get('HIG')
    DBSession.add(output1)

    # admin div (code 30) also has another hazardset
    # but this one is for FL
    # => test outcome = hazardset1b
    output1b = Output()
    output1b.hazardset = hazardset1b
    output1b.administrativedivision = admin30
    output1b.hazardlevel = HazardLevel.get('NPR')
    DBSession.add(output1b)

    # admin div (code 31) has 2 hazardsets,
    # one with a higher calculation_method_quality
    # => test outcome = hazardset2
    admin31 = DBSession.query(AdministrativeDivision)\
        .filter(AdministrativeDivision.code == 31).one()
    output2 = Output()
    output2.hazardset = hazardset1  # calculation_method_quality = 0
    output2.administrativedivision = admin31
    output2.hazardlevel = HazardLevel.get('MED')
    DBSession.add(output2)
    output3 = Output()
    output3.hazardset = hazardset2  # calculation_method_quality = 1
    output3.administrativedivision = admin31
    output3.hazardlevel = HazardLevel.get('LOW')
    DBSession.add(output3)

    # admin div (code 32) has 2 hazardsets,
    # both share the same calculation_method_quality,
    # one with a higher scientific_quality
    # => test outcome = hazardset3
    admin32 = DBSession.query(AdministrativeDivision)\
        .filter(AdministrativeDivision.code == 32).one()
    output4 = Output()
    output4.hazardset = hazardset2
    # calculation_method_quality = 1 / scientific_quality = 0
    output4.administrativedivision = admin32
    output4.hazardlevel = HazardLevel.get('MED')
    DBSession.add(output4)
    output5 = Output()
    output5.hazardset = hazardset3
    # calculation_method_quality = 1 / scientific_quality = 2
    output5.administrativedivision = admin32
    output5.hazardlevel = HazardLevel.get('LOW')
    DBSession.add(output5)

    # admin div (code 33) has 2 hazardsets,
    # both share the same ratings, one is global, one local
    # => test outcome = hazardset4
    admin33 = DBSession.query(AdministrativeDivision)\
        .filter(AdministrativeDivision.code == 33).one()
    output6 = Output()
    output6.hazardset = hazardset3
    # global / calculation_method_quality = 1 / scientific_quality = 2
    output6.administrativedivision = admin33
    output6.hazardlevel = HazardLevel.get('MED')
    DBSession.add(output6)
    output7 = Output()
    output7.hazardset = hazardset4
    # local / calculation_method_quality = 1 / scientific_quality = 2
    output7.administrativedivision = admin33
    output7.hazardlevel = HazardLevel.get('LOW')
    DBSession.add(output7)

    # admin div (code 34) has 2 hazardsets,
    # both share the same ratings, are local, one is more recent
    # => test outcome = hazardset5
    admin34 = DBSession.query(AdministrativeDivision)\
        .filter(AdministrativeDivision.code == 34).one()
    output8 = Output()
    output8.hazardset = hazardset4
    # date = 2015-01-01 / local /
    # calculation_method_quality = 1 / scientific_quality = 2
    output8.administrativedivision = admin34
    output8.hazardlevel = HazardLevel.get('MED')
    DBSession.add(output8)
    output9 = Output()
    output9.hazardset = hazardset5
    # date = now() / local /
    # calculation_method_quality = 1 / scientific_quality = 2
    output9.administrativedivision = admin34
    output9.hazardlevel = HazardLevel.get('LOW')
    DBSession.add(output9)

    # admin div (code 35) has 2 hazardsets,
    # both share the same ratings, are global, one is more recent
    # => test outcome = hazardset6
    admin35 = DBSession.query(AdministrativeDivision)\
        .filter(AdministrativeDivision.code == 35).one()
    output10 = Output()
    output10.hazardset = hazardset3
    # date = 2015-01-01 / global /
    # calculation_method_quality = 1 / scientific_quality = 2
    output10.administrativedivision = admin35
    output10.hazardlevel = HazardLevel.get('MED')
    DBSession.add(output10)
    output11 = Output()
    output11.hazardset = hazardset6
    # date = now() / global /
    # calculation_method_quality = 1 / scientific_quality = 2
    output11.administrativedivision = admin35
    output11.hazardlevel = HazardLevel.get('LOW')
    DBSession.add(output11)

    DBSession.flush()


class TestDecisionTree(unittest.TestCase):

    def setUp(self):  # NOQA
        populate()
