import ConfigParser
from sqlalchemy import engine_from_config
from pyramid.paster import (
    get_appsettings,
)
from .. import load_local_settings
from ..scripts.initializedb import initdb

local_settings_path = 'local.tests.ini'

# raise an error if the file doesn't exist
with open(local_settings_path):
    pass


def populatedb():
    config = ConfigParser.ConfigParser()
    config.read(local_settings_path)
    settings = get_appsettings('development.ini', options={})

    settings['local_settings_path'] = local_settings_path
    load_local_settings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    initdb(engine, True)

populatedb()
