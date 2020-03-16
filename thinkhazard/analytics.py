
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 by the GFDRR / World Bank
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

from requests_futures.sessions import FuturesSession
from urllib.parse import urlencode
import os


class GoogleAnalytics:
    def __init__(self):
        self.tracking_id = 'UA-75301865-1'
        self.debug = "" if os.environ['INI_FILE'] == "production.ini" else "/debug"

    def hit(self, api_path, title):
        params = {
            "v": "1",
            "tid": self.tracking_id,
            "cid": "api",
            "t": "pageview",
            "dt": "API - {}".format(title),
            "dp": api_path
        }
        payload = urlencode(params)
        session = FuturesSession()
        r = session.get("https://www.google-analytics.com{}/collect?{}".format(self.debug, payload))
        if self.debug == "/debug":
            response = r.result()
            print(response.content)
