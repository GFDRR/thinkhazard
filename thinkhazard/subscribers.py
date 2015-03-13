from pyramid.events import subscriber, BeforeRender


@subscriber(BeforeRender)
def add_renderer_globals(event):
    request = event.get('request')
    event['node_modules'] = request.registry.settings.get('node_modules')
    event['debug'] = 'debug' in request.params
