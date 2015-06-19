from pyramid.paster import get_app
application = get_app(
  '{{APP_INI_FILE}}', 'main')
