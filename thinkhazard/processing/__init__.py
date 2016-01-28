import os
import yaml
from pyramid.paster import (
    get_appsettings,
    )
from .. import load_local_settings


def load_settings():
    settings = get_appsettings('development.ini')

    root_folder = os.path.join(os.path.dirname(__file__), '..', '..')
    main_settings_path = os.path.join(root_folder,
                                      'thinkhazard_processing.yaml')
    with open(main_settings_path, 'r') as f:
        settings.update(yaml.load(f.read()))

    load_local_settings(settings)

    return settings

settings = load_settings()


def layer_path(layer):
    return os.path.join(settings['data_path'],
                        'hazardsets',
                        layer.filename())
