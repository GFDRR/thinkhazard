from pyramid.view import view_config

from thinkhazard_common.models import (
    DBSession,
    HazardType,
    )


@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    return {'hazards': hazard_types}
