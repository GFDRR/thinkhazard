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
from datetime import datetime
from subprocess import call
from urllib.parse import urlparse

from pyramid.paster import get_appsettings, setup_logging

from pyramid.scripts.common import parse_vars

from sqlalchemy import engine_from_config

from thinkhazard import lock_file
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
    # practical for debug use in container
    # config_uri = 'c2c://' + argv[1]
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)

    admin_database = database_name(config_uri, "admin", options=options)
    public_database = database_name(config_uri, "public", options=options)

    # TODO: adapt to new infra?
    print("Lock public application in maintenance mode")
    with open(lock_file, "w") as f:
        f.write("This file sets the public application in maintenance mode.")

    # Create new publication in admin database
    print("Log event to publication table in", admin_database)
    settings = get_appsettings(config_uri, name="admin", options=options)
    load_local_settings(settings, "admin")
    engine = engine_from_config(settings, "sqlalchemy.")
    with engine.begin() as db:
        dbsession = get_session_factory(db)()
        Publication.new()
        dbsession.flush()

    backup_filename = "thinkhazard.backup"
    folder_path = settings["backup_path"]
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    backup_path = os.path.join(
        folder_path, backup_filename
    )

    print("Backup", admin_database, "to", backup_path)
    # TODO: adapt to new infra? => do we need to pass credentials to pg commands?
    # pg_user = settings.global_conf['PGUSER']
    # pg_password = settings.global_conf['PGPASSWORD']
    # cmd = "PGPASSWORD=" + pg_password + " pg_dump -U " + pg_user + " -Fc {} > {}".format(admin_database, backup_path)
    cmd = "pg_dump -n datamart -n processing -Fc {} > {}".format(admin_database, backup_path)
    call(cmd, shell=True)

    print("Load backup to S3 bucket")
    s3_helper = S3Helper(
        endpoint_url=settings["aws_endpoint_url"],
        aws_access_key_id=settings["aws_access_key_id"],
        aws_secret_access_key=settings["aws_secret_access_key"])

    if not s3_helper.bucket_exists(settings["aws_bucket_name"]):
        s3_helper.create_bucket(settings["aws_bucket_name"])

    s3_helper.upload_file(backup_path, settings["aws_bucket_name"], backup_filename)

    print("Drop database schemas datamart, processing from", public_database)
    call(["psql", "-d", public_database, "-c", "DROP SCHEMA IF EXISTS datamart, processing CASCADE;"])

    print("Create new fresh database schemas datamart, processing in", public_database)
    call(["psql", "-d", public_database, "-c", "CREATE SCHEMA datamart, processing;"])

    print("Restore backup into", public_database)
    call(
        [
            "pg_restore",
            "--exit-on-error",
            "-d",
            public_database,
            backup_path,
        ]
    )

    print("Delete backup file from filesystem")
    cmd_delete = "rm " + backup_path
    call(cmd_delete, shell=True)

    # TODO: adapt to new infra in tween
    print("Restarting Apache to clear cached data")
    call(["sudo", "apache2ctl", "graceful"])

    print("Unlock public application from maintenance mode")
    os.unlink(lock_file)
