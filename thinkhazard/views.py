import itertools

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from .models import DBSession, Admin0, Admin1, Admin2


def roundrobin(*iterables, **kwargs):
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


@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    return {}


@view_config(route_name='report', renderer='templates/report.jinja2')
def report(request):
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
        'hazards': hazards
    }


@view_config(route_name='adminunit', renderer='json')
def adminunit(request):

    if 'q' not in request.params:
        raise HTTPBadRequest(detail='parameter "q" is missing')

    ilike = '%s%%' % request.params['q']

    admin0s = DBSession.query(Admin0).filter(
        Admin0.name.ilike(ilike)).limit(10)
    admin1s = DBSession.query(Admin1).filter(
        Admin1.name.ilike(ilike)).limit(10)
    admin2s = DBSession.query(Admin2).filter(
        Admin2.name.ilike(ilike)).limit(10)

    data = sorted(roundrobin(admin0s, admin1s, admin2s, limit=10),
                  key=lambda o: o.order)

    return {'data': data}
