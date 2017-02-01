# -*- coding: utf-8 -*-
import sys
from urlparse import urlparse
from sqlalchemy import engine_from_config

from pyramid.paster import get_appsettings

import polib
from ..models import (
    DBSession,
    ClimateChangeRecommendation as CCR,
    TechnicalRecommendation as TR,
    HazardCategory as HC,
    )

from .. import load_local_settings

LOCALE_PATH = 'thinkhazard/locale/%s/LC_MESSAGES/thinkhazard-database.po'
LOCALE_LIST = ('fr', 'es')

def database_name(config_uri, name, options={}):
    settings = get_appsettings(config_uri, name=name, options=options)
    load_local_settings(settings, name)
    url = settings['sqlalchemy.url']
    return urlparse(url).path.strip('/')

def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]

    admin_database = database_name(config_uri, 'admin')
    settings = get_appsettings(config_uri, name='admin')
    load_local_settings(settings, 'admin')
    engine = engine_from_config(settings, 'sqlalchemy.')
    with engine.begin() as db:
        DBSession.configure(bind=db)
        map(import_lang, LOCALE_LIST)

def import_lang(lang):
    po = polib.pofile(LOCALE_PATH % lang)
    total = 0
    for entry in [ e for e in po ]:
        msgid = entry.msgid
        params = { 'text_%s' % lang : entry.msgstr }
        total += (DBSession.query(HC).filter(HC.general_recommendation == msgid).update({
            'general_recommendation_%s' % lang : entry.msgstr }))
        total += (DBSession.query(TR).filter(TR.text == msgid).update({
            'text_%s' % lang : entry.msgstr }))
        total += (DBSession.query(TR).filter(TR.detail == msgid).update({
            'detail_%s' % lang : entry.msgstr }))
        total += (DBSession.query(CCR).filter(CCR.text == msgid).update({
            'text_%s' % lang : entry.msgstr }))
    print '[%s] %s strings updated' % (lang, total)
    DBSession.flush()
