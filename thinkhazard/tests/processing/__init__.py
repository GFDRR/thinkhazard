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

from shapely.geometry import (
    MultiPolygon,
    Polygon,
    )
from geoalchemy2.shape import from_shape

from ...models import (
    DBSession,
    AdminLevelType,
    AdministrativeDivision,
    )


def populate_datamart():
    print 'populate datamart'
    DBSession.query(AdministrativeDivision).delete()

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
