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

import random
import uuid

from shapely.geometry import (
    MultiPolygon,
    Polygon,
    )
from geoalchemy2.shape import from_shape

from ...models import (
    DBSession,
    AdminLevelType,
    AdministrativeDivision,
    Region,
    )


def populate_datamart():
    print('populate datamart')
    DBSession.query(AdministrativeDivision).delete()

    adminlevel_cou = AdminLevelType.get('COU')
    adminlevel_pro = AdminLevelType.get('PRO')
    adminlevel_reg = AdminLevelType.get('REG')

    shape = MultiPolygon([
        Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    ])
    geometry = from_shape(shape, 4326)

    country = AdministrativeDivision(**{
        'code': 10,
        'leveltype_id': adminlevel_cou.id,
        'name': 'Administrative division level 1'
    })
    region = Region(id=random.randint(0, 0xffffff),
                    name=uuid.uuid4(), level=3)
    DBSession.add(region)
    country.regions = [region]
    DBSession.add(country)

    province = AdministrativeDivision(**{
        'code': 20,
        'leveltype_id': adminlevel_pro.id,
        'name': 'Administrative division level 2'
    })
    province.parent = country
    DBSession.add(province)

    div = AdministrativeDivision(**{
        'code': 30,
        'leveltype_id': adminlevel_reg.id,
        'name': 'Administrative division level 3'
    })
    div.geom = geometry
    div.hazardcategories = []
    div.parent = province

    DBSession.add(div)

    DBSession.flush()
