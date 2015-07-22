from pyramid.view import view_config

from ..models import (
    DBSession,
    HazardType)


@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    hazard_types = DBSession.query(HazardType)
    return {'hazards': hazard_types}
