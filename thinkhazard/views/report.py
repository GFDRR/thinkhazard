from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from ..models import DBSession, AdministrativeDivision


@view_config(route_name='report', renderer='templates/report.jinja2')
def report(request):
    try:
        divisioncode = int(request.params.get('divisioncode'))
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    division = DBSession.query(AdministrativeDivision).filter(
        AdministrativeDivision.code == divisioncode).one()

    hazards = [{
        'name': 'drought',
        'level': 'high'
    }, {
        'name': 'earthquake',
        'level': 'high'
    }, {
        'name': 'tsunami',
        'level': 'high'
    }, {
        'name': 'flood',
        'level': 'medium'
    }, {
        'name': 'storm-surge',
        'level': 'medium'
    }, {
        'name': 'strong-wind',
        'level': 'low'
    }, {
        'name': 'volcanic-ash',
        'level': 'no-evidence'
    }]
    return {
        'hazards': hazards,
        'division': division
    }
