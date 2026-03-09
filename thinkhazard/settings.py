import os
import configparser
from pyramid.paster import get_appsettings


def load_full_settings(config_uri, name="admin", options={}):
    """Load app settings, processing settings and local settings.
    Fallback to admin app by default as this should mainly be used by admin
    scripts.
    """
    settings = get_appsettings(
        config_uri,
        name=name,
        options={
            **options,
        }
    )
    load_local_settings(settings, name)
    load_processing_settings(settings)
    return settings


def load_processing_settings(settings):
    """Load processing specific settings.
    """
    # Still needed for further resources
    settings["geonode"] = {
        "url": os.environ["GEONODE_URL"],
        "username": os.environ["GEONODE_USERNAME"],
        "api_key": os.environ["GEONODE_API_KEY"]
    }


def load_local_settings(settings, name):
    """ Load local/user-specific settings.
    """
    local_settings_path = os.environ.get(
        "LOCAL_SETTINGS_PATH", settings.get("local_settings_path")
    )
    if local_settings_path and os.path.exists(local_settings_path):
        config = configparser.ConfigParser()
        config.read(local_settings_path)
        settings.update(config.items("app:{}".format(name)))
