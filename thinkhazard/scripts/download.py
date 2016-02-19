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

import sys
import argparse
from sqlalchemy import engine_from_config

from ..models import DBSession

from ..processing import settings
from ..processing.downloading import download


def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--hazardset_id', dest='hazardset_id', action='store',
        help='The hazardset id')
    parser.add_argument(
        '--force', dest='force',
        action='store_const', const=True, default=False,
        help='Force download even if layer has already been downloaded')
    parser.add_argument(
        '--dry-run', dest='dry_run',
        action='store_const', const=True, default=False,
        help='Perform a trial run that does not commit changes')
    args = parser.parse_args(argv[1:])

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)

    download(
        hazardset_id=args.hazardset_id,
        force=args.force,
        dry_run=args.dry_run)
