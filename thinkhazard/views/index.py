from pyramid.view import view_config


@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    return {}
