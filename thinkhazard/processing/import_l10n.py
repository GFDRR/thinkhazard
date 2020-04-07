# -*- coding: utf-8 -*-
import polib

from thinkhazard.models import (
    ClimateChangeRecommendation as CcRec,
    TechnicalRecommendation as TecRec,
    HazardCategory as HazCat,
)
from thinkhazard.processing import BaseProcessor

LOCALE_PATH = "/tmp/thinkhazard-database-{lang}.po"
LOCALE_LIST = ("fr", "es")


class L10nImporter(BaseProcessor):

    def do_execute(self):
        list(map(self.import_lang, LOCALE_LIST))

    def import_lang(self, lang):
        po = polib.pofile(LOCALE_PATH.format(lang=lang))
        total = 0
        for entry in [e for e in po]:
            msgid = entry.msgid
            params = {"text_%s" % lang: entry.msgstr}
            total += (
                self.dbsession.query(HazCat)
                .filter(HazCat.general_recommendation == msgid)
                .update({"general_recommendation_%s" % lang: entry.msgstr})
            )
            total += self.dbsession.query(TecRec).filter(TecRec.text == msgid).update(params)
            total += (
                self.dbsession.query(TecRec)
                .filter(TecRec.detail == msgid)
                .update({"detail_%s" % lang: entry.msgstr})
            )
            total += self.dbsession.query(CcRec).filter(CcRec.text == msgid).update(params)
        print("[%s] %s strings updated" % (lang, total))
        self.dbsession.flush()
