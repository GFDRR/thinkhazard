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

from mock import patch

from thinkhazard.processing.publish import Publisher

from .. import engine, DBSession, settings
from . import BaseTestCase


class TestPublisher(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        # Override parent method to avoid idle transaction when dropping schemas
        pass

    def publisher(self):
        publisher = Publisher()
        publisher.engine = engine
        publisher.dbsession = DBSession
        publisher.settings = settings
        return publisher

    @patch.object(Publisher, "do_execute")
    def test_cli(self, mock):
        """Test publisher cli"""
        Publisher.run(["publish", "--config_uri", "c2c://tests.ini"])
        mock.assert_called_with()

    def test_execute(self):
        """Test publisher"""
        self.publisher().execute()
