import json
import itertools
import mapnik

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from sqlalchemy import and_

import geoalchemy2.shape

from ..models import (
    DBSession,
    AdminLevelType,
    AdministrativeDivision,
    CategoryType,
    HazardType
    )


def _create_map_object(division_code, hazard_type, mapfile, rasterfile,
                       width, height):
    """
    Create a Mapnik map for an administrative division.
    """

    map_ = mapnik.Map(width, height)
    mapnik.load_map(map_, mapfile)

    raster_datasource = mapnik.Gdal(file=rasterfile)
    layer = mapnik.Layer('raster')
    layer.srs = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
    layer.styles.append('raster')
    layer.datasource = raster_datasource
    map_.layers.append(layer)

    division_geometry, division_leveltype = DBSession.query(
        AdministrativeDivision.geometry_wgs84, AdminLevelType.mnemonic) \
        .join(AdministrativeDivision.leveltype) \
        .filter(AdministrativeDivision.code == division_code).one()

    division_shape = geoalchemy2.shape.to_shape(division_geometry)
    division_box = mapnik.Box2d(*division_shape.bounds)

    _filter = None
    if division_leveltype == u'REG':
        _filter = AdministrativeDivision.code == division_code
    else:
        _filter = AdministrativeDivision.parent_code == division_code

    if hazard_type is not None:
        subdivisions = DBSession.query(AdministrativeDivision,
                                       CategoryType.mnemonic) \
            .outerjoin(AdministrativeDivision.hazardcategories) \
            .outerjoin(HazardType).outerjoin(CategoryType) \
            .filter(and_(_filter, HazardType.mnemonic == hazard_type))
    else:
        subdivisions = itertools.izip(
            DBSession.query(AdministrativeDivision).filter(_filter),
            itertools.chain('NONE'))

    division_datasource = mapnik.MemoryDatasource()

    for subdivision, category in subdivisions:
        feature = mapnik.Feature(mapnik.Context(), subdivision.id)
        feature['name'] = subdivision.name
        feature['code'] = subdivision.code
        feature['category'] = category
        shape = geoalchemy2.shape.to_shape(subdivision.geometry_wgs84)
        feature.add_geometries_from_wkb(shape.wkb)
        division_datasource.add_feature(feature)

    layer = mapnik.Layer('admindiv')
    layer.srs = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 ' \
                '+x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null ' \
                '+wktext +no_defs +over" background-color="#b8dee6"'
    layer.styles.append('admindiv')
    layer.styles.append('admindivcommon')
    layer.datasource = division_datasource

    map_.layers.append(layer)
    map_.zoom_to_box(division_box)

    return map_


@view_config(route_name='map')
def mapnikmap(request):
    params = request.params

    try:
        division_code = int(params.get('divisioncode'))
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    hazard_type = params.get('hazardtype')

    try:
        width = int(params.get('width'))
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"width"')

    try:
        height = int(params.get('height'))
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"height"')

    format_ = request.matchdict['format']
    if format_ not in (u'json', u'jpeg', u'png'):
        raise HTTPBadRequest(detail='format %s is not supported' % format_)
    format_ = str(format_)

    mapfile = request.registry.settings.get('mapfile')
    rasterfile = request.registry.settings.get('rasterfile')

    map_ = _create_map_object(division_code, hazard_type,
                              mapfile, rasterfile, width, height)

    if format_ == 'json':
        grid = mapnik.Grid(width, height)
        mapnik.render_layer(map_, grid, layer=1, fields=['name', 'code'])
        utfgrid = grid.encode('utf', resolution=4)
        request.response.content_type = 'application/json'
        request.response.body = json.dumps(utfgrid)
    else:
        image = mapnik.Image(width, height)
        mapnik.render(map_, image, 1, 1)
        request.response.content_type = 'image/%s' % format_
        request.response.body = image.tostring(format_)

    return request.response
