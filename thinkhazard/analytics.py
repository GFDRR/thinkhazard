
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
        self.debug = "/debug" if os.environ['INI_FILE'] == "development.ini" else ""

    def hit(self, api_path, title):
        params = {
            "v": "1",
            "tid": self.tracking_id,
            "cid": "api",
            "t": "pageview",
            "dt": "API - {}".format(title),
            # "ec": "api",
            # "ea": "hazardset",
            # "dh": 'www.thinkhazard.org',
            "dp": api_path
        }
        payload = urlencode(params)
        session = FuturesSession()
        r = session.get("https://www.google-analytics.com{}/collect?{}".format(self.debug, payload))
        response = r.result()
        print('GA response status: {0}'.format(response.status_code))
        # print(response.content)
        if not response.status_code == 200:
            print('GA not responding')


# Attempt to implement async request without requests_futures
# from webob import Request
# from urllib.parse import urlencode
# import asyncio


# async def send_request(tracking_id, hit_type):
#     params = {
#         "v": "v1",
#         "tid": tracking_id,
#         "t": hit_type
#     }
#     payload = urlencode(params)
#     r = Request.blank("https://www.google-analytics.com/collect?{}".format(payload))
#     r.send()
#     print(r)


# class GoogleAnalytics:
#     def __init__(self):
#         # TODO : replace by 'UA-75358940-1'
#         self.tracking_id = ''

#     def hit(self, hit_type):
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         task = loop.create_task(send_request(self.tracking_id, hit_type))
#         loop.run_until_complete(task)