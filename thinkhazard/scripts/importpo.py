# -*- coding: utf-8 -*-
import sys
from urllib.parse import urlparse
from sqlalchemy import engine_from_config

from pyramid.paster import get_appsettings

import polib
from thinkhazard.models import (
    ClimateChangeRecommendation as CcRec,
    TechnicalRecommendation as TecRec,
    HazardCategory as HazCat,
)
from thinkhazard.session import get_session_factory
from thinkhazard import load_local_settings

LOCALE_PATH = "thinkhazard/locale/%s/LC_MESSAGES/thinkhazard-database.po"
LOCALE_LIST = ("fr", "es")


def database_name(config_uri, name, options={}):
    settings = get_appsettings(config_uri, name=name, options=options)
    load_local_settings(settings, name)
    url = settings["sqlalchemy.url"]
    return urlparse(url).path.strip("/")


def main(argv=sys.argv):
    config_uri = argv[1]

    settings = get_appsettings(config_uri, name="admin")
    load_local_settings(settings, "admin")
    engine = engine_from_config(settings, "sqlalchemy.")
    dbsession = get_session_factory(engine)()
    with engine.begin() as db:
        dbsession.configure(bind=db)
        list(map(import_lang, LOCALE_LIST))


def import_lang(dbsession, lang):
    po = polib.pofile(LOCALE_PATH % lang)
    total = 0
    for entry in [e for e in po]:
        msgid = entry.msgid
        params = {"text_%s" % lang: entry.msgstr}
        total += (
            dbsession.query(HazCat)
            .filter(HazCat.general_recommendation == msgid)
            .update({"general_recommendation_%s" % lang: entry.msgstr})
        )
        total += dbsession.query(TecRec).filter(TecRec.text == msgid).update(params)
        total += (
            dbsession.query(TecRec)
            .filter(TecRec.detail == msgid)
            .update({"detail_%s" % lang: entry.msgstr})
        )
        total += dbsession.query(CcRec).filter(CcRec.text == msgid).update(params)
    print("[%s] %s strings updated" % (lang, total))
    dbsession.flush()
