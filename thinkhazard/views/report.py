from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from ..models import DBSession, \
    AdministrativeDivision, HazardType, CategoryType


@view_config(route_name='report', renderer='templates/report.jinja2')
def report(request):
    try:
        divisioncode = int(request.params.get('divisioncode'))
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"divisioncode"')

    division = DBSession.query(AdministrativeDivision).filter(
        AdministrativeDivision.code == divisioncode).one()

    hs = DBSession.query(HazardType.mnemonic, HazardType.title) \
        .all()

    hazards = {}
    for mnemonic, name in hs:
        hazards[mnemonic] = {
            'mnemonic': mnemonic,
            'name': name,
            'level': 'no-data'
        }

    ls = DBSession.query(HazardType.mnemonic,
                         HazardType.title,
                         CategoryType.mnemonic) \
        .outerjoin(AdministrativeDivision.hazardcategories) \
        .outerjoin(HazardType) \
        .outerjoin(CategoryType) \
        .filter(AdministrativeDivision.code == divisioncode).all()

    for mnemonic, name, level in ls:
        if mnemonic is not None:
            hazards[mnemonic]['level'] = level

    hs = []
    for mnemonic in hazards:
        hs.append(hazards[mnemonic])

    return {
        'hazards': hs,
        'division': division
    }
