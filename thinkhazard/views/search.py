import itertools

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from sqlalchemy import and_

from ..models import (
    DBSession,
    AdministrativeDivision,
    )


def _roundrobin(*iterables, **kwargs):
    """
    This function is a derivate of the roundrobin function provided in the
    itertools documentation page.

    https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    limit = kwargs.get('limit', float('inf'))
    pending = len(iterables)
    nexts = itertools.cycle(iter(it).next for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
                limit -= 1
                if limit == 0:
                    return
        except StopIteration:
            pending -= 1
            nexts = itertools.cycle(itertools.islice(nexts, pending))


@view_config(route_name='administrativedivision', renderer='json')
def administrativedivision(request):

    if 'q' not in request.params:
        raise HTTPBadRequest(detail='parameter "q" is missing')

    ilike = '%%%s%%' % request.params['q']

    admin0s = DBSession.query(AdministrativeDivision).filter(
        and_(AdministrativeDivision.leveltype_id == 1,
             AdministrativeDivision.name.ilike(ilike))).limit(10)

    admin1s = DBSession.query(AdministrativeDivision).filter(
        and_(AdministrativeDivision.leveltype_id == 2,
             AdministrativeDivision.name.ilike(ilike))).limit(10)

    admin2s = DBSession.query(AdministrativeDivision).filter(
        and_(AdministrativeDivision.leveltype_id == 3,
             AdministrativeDivision.name.ilike(ilike))).limit(10)

    data = sorted(_roundrobin(admin0s, admin1s, admin2s, limit=10),
                  key=lambda o: o.leveltype_id)

    return {'data': data}
