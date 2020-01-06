# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 by the GFDRR / World Bank
#
# This file is part of ThinkHazard.
#
# ThinkHazard is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# ThinkHazard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# ThinkHazard.  If not, see <http://www.gnu.org/licenses/>.

from lingua.extractors import Extractor
from lingua.extractors import Message

from sqlalchemy import engine_from_config
from thinkhazard.settings import load_full_settings

from thinkhazard.models import (
    DBSession,
    ClimateChangeRecommendation,
    HazardCategory,
    HazardLevel,
    HazardType,
    TechnicalRecommendation,
)


class EnumExtractor(Extractor):

    # fake extension but working for at least one file
    extensions = ['.enum-i18n']

    def __call__(self, filename, options):

        # FIXME find a better way to load settings
        settings = load_full_settings('development.ini')

        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)

        messages = []

        for rec in DBSession.query(HazardLevel):
            messages.append((rec.title, type(rec).__name__))

        for rec in DBSession.query(HazardType):
            messages.append((rec.title, type(rec).__name__))

        return [
            Message(None, text, None, [],
                    class_name,
                    '', (filename, 1))
            for text, class_name in messages if text != '' and text is not None
        ]


class DatabaseExtractor(Extractor):

    # fake extension but working for at least one file
    extensions = ['.db-i18n']

    def __call__(self, filename, options):

        # FIXME find a better way to load settings
        settings = load_full_settings('development.ini')

        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)

        messages = []

        for rec in DBSession.query(ClimateChangeRecommendation):
            messages.append((rec.text, type(rec).__name__))

        for rec in DBSession.query(HazardCategory):
            messages.append((rec.general_recommendation, type(rec).__name__))

        for rec in DBSession.query(TechnicalRecommendation):
            messages.append((rec.text, type(rec).__name__))
            messages.append((rec.detail, type(rec).__name__))

        return [
            Message(None, text, None, [],
                    class_name,
                    '', (filename, 1))
            for text, class_name in messages if text != '' and text is not None
        ]
