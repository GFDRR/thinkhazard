from pyramid.view import view_config

from thinkhazard_common.models import (
    DBSession,
    HazardType,
    )


@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    return {'hazards': hazard_types}


@view_config(route_name='about', renderer='templates/about.jinja2')
def about(request):
    return {}


@view_config(route_name='faq', renderer='templates/faq.jinja2')
def faq(request):
    return {}
