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

import time
from sqlalchemy.sql import text


def wait_for_db(connection):
    sleep_time = 1
    max_sleep = 30
    while sleep_time < max_sleep:
        try:
            connection.execute(text("SELECT 1;"))
            return
        except Exception as e:
            print(str(e))
            print("Waiting for the DataBase server to be reachable")
            time.sleep(sleep_time)
            sleep_time *= 2
    exit(1)
