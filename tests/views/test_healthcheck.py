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

from . import BaseTestCase


class TestHeathcheckFunction(BaseTestCase):

    @patch("thinkhazard.tweens.Publication.last",
           side_effect=Exception("Healthcheck should not raise exception while publishing"))
    def test_healthcheck(self, last_mock):
        self.testapp.get("/healthcheck", status=200)
