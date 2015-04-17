import json
import mapnik

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

import geoalchemy2.shape

from ..models import DBSession, AdministrativeDivision


def _create_map_object(division_code, mapfile, rasterfile, width, height):
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

    division_geometry = DBSession.query(
        AdministrativeDivision.geometry_wgs84).filter(
        AdministrativeDivision.code == division_code).scalar()
    division_shape = geoalchemy2.shape.to_shape(division_geometry)
    division_box = mapnik.Box2d(*division_shape.bounds)

    subdivisions = DBSession.query(AdministrativeDivision).filter(
        AdministrativeDivision.parent_code == division_code)

    division_datasource = mapnik.MemoryDatasource()

    for subdivision in subdivisions:
        feature = mapnik.Feature(mapnik.Context(), subdivision.id)
        feature['name'] = subdivision.name
        feature['code'] = subdivision.code
        shape = geoalchemy2.shape.to_shape(subdivision.geometry_wgs84)
        feature.add_geometries_from_wkb(shape.wkb)
        division_datasource.add_feature(feature)

    layer = mapnik.Layer('admindiv')
    layer.srs = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 ' \
                '+x_0=0.0 +y_0=0.0 +k=1.0 +units=m +nadgrids=@null ' \
                '+wktext +no_defs +over" background-color="#b8dee6"'
    layer.styles.append('admindiv')
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

    mapfile = request.registry.settings.get('mapfile')
    rasterfile = request.registry.settings.get('rasterfile')

    map_ = _create_map_object(division_code, mapfile, rasterfile,
                              width, height)

    format_ = request.matchdict['format']

    if format_ == 'json':
        grid = mapnik.Grid(width, height)
        mapnik.render_layer(map_, grid, layer=1, fields=['name', 'code'])
        utfgrid = grid.encode('utf', resolution=4)
        request.response.content_type = 'application/json'
        request.response.body = json.dumps(utfgrid)
    else:
        image = mapnik.Image(width, height)
        mapnik.render(map_, image, 1, 1)
        request.response.content_type = 'image/png'
        request.response.body = image.tostring('png')

    return request.response
