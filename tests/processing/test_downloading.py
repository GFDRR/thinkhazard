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

import unittest
import transaction
from mock import patch

from thinkhazard.processing.downloading import Downloader

from .. import settings
from . import populate_datamart


def populate():
    populate_datamart()
    transaction.commit()


class TestDownloading(unittest.TestCase):
    def setUp(self):  # NOQA
        populate()

    @patch.object(Downloader, "do_execute")
    def test_cli(self, mock):
        """Test downloader cli"""
        Downloader.run(["complete", "--config_uri", "c2c://tests.ini"])
        mock.assert_called_with(hazardset_id=None, clear_cache=False)

    def test_force(self):
        """Test downloader in force mode"""
        Downloader().execute(settings, force=True)
