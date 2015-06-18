from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from papyrus.renderers import GeoJSON

from .models import (
    DBSession,
    Base,
    )


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.include('pyramid_jinja2')
    config.include('papyrus')

    config.add_static_view('static', 'static', cache_max_age=3600,
                           cachebust=True)
    config.add_static_view('lib', settings.get('node_modules'),
                           cache_max_age=86000, cachebust=True)

    config.add_route('index', '/')
    config.add_route('report',
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}')
    config.add_route('report_json',
                     '/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}.json')
    config.add_route('report_overview', '/report/{divisioncode:\d+}')
    config.add_route('report_overview_json', '/report/{divisioncode:\d+}.json')
    config.add_route('administrativedivision', '/administrativedivision')

    config.add_renderer('geojson', GeoJSON())

    config.scan()
    return config.make_wsgi_app()
