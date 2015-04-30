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
        'level': 'HIG'
    }, {
        'mnemonic': 'EQ',
        'name': 'earthquake',
        'level': 'HIG'
    }, {
        'mnemonic': 'TS',
        'name': 'tsunami',
        'level': 'HIG'
    }, {
        'mnemonic': 'FL',
        'name': 'flood',
        'level': 'MED'
    }, {
        'mnemonic': 'SS',
        'name': 'storm-surge',
        'level': 'MED'
    }, {
        'mnemonic': 'SW',
        'name': 'strong-wind',
        'level': 'LOW'
    }, {
        'mnemonic': 'VA',
        'name': 'volcanic-ash',
        'level': 'NPR'
    }]
    return {
        'hazards': hazards,
        'division': division
    }
