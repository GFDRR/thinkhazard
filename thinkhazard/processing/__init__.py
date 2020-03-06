# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 by the GFDRR / World Bank
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

import sys
import argparse
import os
import logging
import colorlog

from thinkhazard.settings import load_full_settings
from thinkhazard.session import get_engine, get_session_factory


logger = colorlog.getLogger(__name__)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
)
ch.setFormatter(formatter)
logger.addHandler(ch)


class BaseProcessor:
    def __init__(self):
        self.force = False

    @classmethod
    def run(cls, argv=sys.argv):
        parser = cls.argument_parser()
        args = vars(parser.parse_args(argv[1:]))

        config_uri = args.pop("config_uri")
        name = args.pop("name")
        settings = load_full_settings(config_uri, name=name)

        processor = cls()
        processor.settings = settings
        processor.engine = get_engine(settings, "sqlalchemy.")
        processor.dbsession = get_session_factory(processor.engine)()
        processor.execute(**args)
        processor.dbsession.commit()

    @staticmethod
    def argument_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--config_uri",
            dest="config_uri",
            default="development.ini",
            help="Configuration uri. Defaults to development.ini",
        )
        parser.add_argument(
            "--name",
            dest="name",
            default="admin",
            help="Application name. Default to admin app",
        )
        parser.add_argument(
            "-f",
            "--force",
            dest="force",
            action="store_const",
            const=True,
            default=False,
            help="Force execution even if layer metadata have already \
                  been fetched",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_const",
            const=True,
            default=False,
            help="Perform a trial run that does not commit changes",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            dest="verbose",
            action="store_const",
            const=True,
            default=False,
            help="Increase verbosity",
        )
        parser.add_argument(
            "-d",
            "--debug",
            dest="debug",
            action="store_const",
            const=True,
            default=False,
            help="Output debugging informations",
        )
        return parser

    def execute(
        self, dry_run=False, force=False, verbose=False, debug=False, **kwargs
    ):
        self.dry_run = dry_run
        self.force = force

        if debug:
            logger.setLevel(logging.DEBUG)
        elif verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        if dry_run:
            t = self.dbsession.begin_nested()

        self.do_execute(**kwargs)

        if dry_run:
            logger.info("Dry run : rolling back transaction")
            t.abort()

    def layer_path(self, layer):
        return os.path.join(self.settings["data_path"], "hazardsets", layer.filename())
