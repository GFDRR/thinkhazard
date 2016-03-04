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

import os
import yaml
import logging
import colorlog
from pyramid.paster import (
    get_appsettings,
    )
from .. import load_local_settings


logger = colorlog.getLogger(__name__)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)-8s %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white'})
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.setLevel(logging.DEBUG)


def load_settings():
    settings = get_appsettings(os.path.join(os.path.dirname(__file__),
                                            '../../development.ini'))

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
