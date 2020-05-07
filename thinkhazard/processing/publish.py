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

import logging
import os
from datetime import datetime
from pkg_resources import resource_filename
from subprocess import run

from pyramid.settings import asbool

from thinkhazard.models import Publication
from thinkhazard.processing import BaseProcessor
from thinkhazard.session import get_session_factory
from thinkhazard.scripts.s3helper import S3Helper

LOG = logging.getLogger(__name__)
LOCAL_BACKUP_PATH = '/tmp/backups/thinkhazard.backup'


class Publisher(BaseProcessor):

    def do_execute(self):
        self.use_cache = asbool(os.environ.get("USE_CACHE", False))

        # TODO: adapt to new infra?
        # print("Lock public application in maintenance mode")
        # with open(lock_file, "w") as f:
        #     f.write("This file sets the public application in maintenance mode.")

        # Create new publication in admin database
        LOG.info("Log event to publication table in admin database")
        with self.engine.begin() as db:
            dbsession = get_session_factory(db)()
            Publication.new(dbsession)
            dbsession.flush()

        admin_env = {
            "PGHOST": os.environ['PGHOST'],
            "PGUSER": os.environ['PGUSER_ADMIN'],
            "PGPASSWORD": os.environ['PGPASSWORD_ADMIN'],
            "PGDATABASE": os.environ['PGDATABASE_ADMIN'],
        }

        if not self.use_cache or not os.path.isfile(LOCAL_BACKUP_PATH):
            LOG.info("Backup admin database to {}".format(LOCAL_BACKUP_PATH))
            if os.path.isfile(LOCAL_BACKUP_PATH):
                os.unlink(LOCAL_BACKUP_PATH)
            run(
                "pg_dump --no-owner -Fc -f '{}'".format(LOCAL_BACKUP_PATH),
                env=admin_env,
                shell=True,
            )

        LOG.info("Load backup to S3 bucket")
        s3_helper = S3Helper(
            self.settings["aws_bucket_name"],
            aws_access_key_id=self.settings["aws_access_key_id"],
            aws_secret_access_key=self.settings["aws_secret_access_key"]
        )
        s3_helper.upload_file(
            LOCAL_BACKUP_PATH,
            "backups/thinkhazard.{}.backup".format(datetime.utcnow().isoformat())
        )

        public_env = {
            "PGHOST": os.environ['PGHOST'],
            "PGUSER": os.environ['PGUSER_PUBLIC'],
            "PGPASSWORD": os.environ['PGPASSWORD_PUBLIC'],
            "PGDATABASE": os.environ['PGDATABASE_PUBLIC'],
        }

        LOG.info("Restore backup into public database")
        run(
            "pg_restore --exit-on-error --no-owner -n datamart -n processing -f - '{backup}'"
            " | {reset_schemas} 'datamart processing'"
            " | psql --single-transaction -d {database}".format(
                backup=LOCAL_BACKUP_PATH,
                reset_schemas=resource_filename("thinkhazard", "scripts/reset-schemas"),
                database=public_env["PGDATABASE"],
            ),
            env=public_env,
            shell=True,
        )

        if not self.use_cache:
            LOG.info("Delete backup file from filesystem")
            os.remove(LOCAL_BACKUP_PATH)

        # TODO: adapt to new infra in tween
        # print("Restarting Apache to clear cached data")
        # call(["sudo", "apache2ctl", "graceful"])

        # print("Unlock public application from maintenance mode")
        # os.unlink(lock_file)
