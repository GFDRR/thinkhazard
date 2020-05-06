
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


class GoogleAnalytics:
    def __init__(self):
        self.debug = False

    def hit(self, request, title):
        params = {
            "v": "1",
            "tid": request.registry.settings['analytics'],
            "cid": "api",
            "t": "pageview",
            "dt": "API - {}".format(title),
            "dp": request.path
        }
        payload = urlencode(params)
        session = FuturesSession()
        debug_url = "/debug" if self.debug else ""
        r = session.get("https://www.google-analytics.com{}/collect?{}".format(debug_url, payload))
        if self.debug:
            response = r.result()
            print(response.content)
