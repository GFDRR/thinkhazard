from pyramid.view import view_config


@view_config(route_name='index', renderer='templates/index.jinja2')
def index(request):
    debug = 'debug' in request.params
    settings = request.registry.settings
    return {'debug': debug,
            'node_modules': settings.get('node_modules')}
