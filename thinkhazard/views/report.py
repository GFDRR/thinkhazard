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
        'mnemonic': 'DG',
        'name': 'drought',
        'level': 'high'
    }, {
        'mnemonic': 'EQ',
        'name': 'earthquake',
        'level': 'high'
    }, {
        'mnemonic': 'TS',
        'name': 'tsunami',
        'level': 'high'
    }, {
        'mnemonic': 'FL',
        'name': 'flood',
        'level': 'medium'
    }, {
        'mnemonic': 'SS',
        'name': 'storm-surge',
        'level': 'medium'
    }, {
        'mnemonic': 'SW',
        'name': 'strong-wind',
        'level': 'low'
    }, {
        'mnemonic': 'VA',
        'name': 'volcanic-ash',
        'level': 'no-evidence'
    }]
    return {
        'hazards': hazards,
        'division': division
    }
