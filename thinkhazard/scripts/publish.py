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

import os
import sys
import tempfile
from subprocess import call
from urllib.parse import urlparse

from pyramid.paster import get_appsettings, setup_logging

from pyramid.scripts.common import parse_vars

from sqlalchemy import engine_from_config

# from thinkhazard import lock_file
from thinkhazard.session import get_session_factory
from thinkhazard.settings import load_local_settings
from thinkhazard.models import Publication
from thinkhazard.scripts.s3helper import S3Helper


def usage(argv):
    cmd = os.path.basename(argv[0])
    print(
        (
            "usage: %s <config_uri> [var=value]\n"
            '(example: "%s development.ini")' % (cmd, cmd)
        )
    )
    sys.exit(1)


def database_name(config_uri, name, options={}):
    settings = get_appsettings(config_uri, name=name, options=options)
    load_local_settings(settings, name)
    url = settings["sqlalchemy.url"]
    return urlparse(url).path.strip("/")


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)

    admin_database = database_name(config_uri, "admin", options=options)
    public_database = database_name(config_uri, "public", options=options)

    # TODO: adapt to new infra?
    # print("Lock public application in maintenance mode")
    # with open(lock_file, "w") as f:
    #     f.write("This file sets the public application in maintenance mode.")

    # Create new publication in admin database
    print("Log event to publication table in", admin_database)
    settings = get_appsettings(config_uri, name="admin", options=options)
    load_local_settings(settings, "admin")
    engine = engine_from_config(settings, "sqlalchemy.")
    with engine.begin() as db:
        dbsession = get_session_factory(db)()
        Publication.new(dbsession)
        dbsession.flush()

    backup_filename = "thinkhazard.backup"
    backup_path = os.path.join(
        tempfile.gettempdir(), backup_filename
    )

    print("Backup", admin_database, "to", backup_path)
    pg_user_admin = settings.global_conf['PGUSER_ADMIN']
    pg_password_admin = settings.global_conf['PGUSER_ADMIN']
    cmd = "PGPASSWORD=" + pg_password_admin + " pg_dump -O -U " + pg_user_admin + \
        " -Fc {} > {}".format(admin_database, backup_path)
    call(cmd, shell=True)

    print("Load backup to S3 bucket")
    s3_helper = S3Helper(
        settings["aws_bucket_name"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"]
    )

    s3_helper.upload_file(backup_path, backup_filename)

    pg_user_public = settings.global_conf['PGUSER_PUBLIC']
    pg_password_public = settings.global_conf['PGUSER_PUBLIC']

    print("Drop database schemas datamart, processing from", public_database)
    cmd_drop = "PGPASSWORD=" + pg_password_public + " psql -U " + pg_user_public + \
        " -d " + public_database + " -c 'DROP SCHEMA IF EXISTS datamart, processing CASCADE';"
    call(cmd_drop, shell=True)

    print("Create new fresh database schemas datamart, processing in", public_database)
    cmd_create_datamart = "PGPASSWORD=" + pg_password_public + " psql -U " + pg_user_public + \
        " -d " + public_database + " -c 'CREATE SCHEMA datamart';"
    cmd_create_processing = "PGPASSWORD=" + pg_password_public + " psql -U " + pg_user_public + \
        " -d " + public_database + " -c 'CREATE SCHEMA processing';"
    call(cmd_create_datamart, shell=True)
    call(cmd_create_processing, shell=True)

    print("Restore backup into", public_database)
    cmd_restore = "PGPASSWORD=" + pg_password_public + " pg_restore -U " + pg_user_public + \
        " --exit-on-error -n datamart -n processing -d " + public_database + " " + backup_path
    print(cmd_restore)
    call(cmd_restore, shell=True)

    print("Delete backup file from filesystem")
    os.remove(backup_path)

    # TODO: adapt to new infra in tween
    # print("Restarting Apache to clear cached data")
    # call(["sudo", "apache2ctl", "graceful"])

    # print("Unlock public application from maintenance mode")
    # os.unlink(lock_file)
