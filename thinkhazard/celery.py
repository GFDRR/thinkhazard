import importlib
import io
import codecs
import logging
import traceback
import os
import subprocess
from contextlib import ContextDecorator
from datetime import datetime
from celery import Celery

from thinkhazard.processing.harvesting import Harvester
from thinkhazard.processing.downloading import Downloader
from thinkhazard.processing.completing import Completer
from thinkhazard.processing.processing import Processor
from thinkhazard.processing.decisiontree import DecisionMaker
from thinkhazard.processing.publish import Publisher
from thinkhazard.processing.import_geopackage import GeopackageImporter
from thinkhazard.lib.s3helper import S3Helper
from thinkhazard.settings import load_full_settings
imp = importlib.import_module("thinkhazard.processing.import")

INI_FILE = os.environ["INI_FILE"]

app = Celery()
app.conf.broker_url = os.environ["BROKER_URL"]


class CaptureTaskLogs(ContextDecorator):
    """Context manager and decorator for capturing task logs and uploading to S3."""

    def __init__(self, task_name):
        self.task_name = task_name
        self.bytes_log = None
        self.log_handler = None
        self.root_logger = None

    def __enter__(self):
        self.settings = load_full_settings(INI_FILE, name="admin")

        self.bytes_log = io.BytesIO()
        stream_writer = codecs.getwriter("utf-8")
        str_log = stream_writer(self.bytes_log)
        self.log_handler = logging.StreamHandler(str_log)
        self.log_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
        self.log_handler.setFormatter(formatter)

        self.root_logger = logging.getLogger()
        self.root_logger.addHandler(self.log_handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.root_logger.error(f"Task {self.task_name} failed with error: {exc_val}")
            self.root_logger.error(traceback.format_exc())

        self.root_logger.removeHandler(self.log_handler)
        self.bytes_log.seek(0)

        try:
            s3_helper = S3Helper(self.settings)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"logs/{self.task_name}_{timestamp}.txt"
            s3_helper.upload_fileobj(self.bytes_log, object_name)
        except Exception as e:
            print(f"Failed to upload log to S3: {e}")

        return False


@app.task
@CaptureTaskLogs("publish")
def publish():
    print("start publish")
    Publisher.run((INI_FILE, "-v"))
    print("end publish")


@app.task
@CaptureTaskLogs("transifex_fetch")
def transifex_fetch():
    print("start transifex_fetch")
    subprocess.run(
        [
            "/app/thinkhazard/scripts/tx-pull-db"
        ],
        check=True
    )
    print("end transifex_fetch")


@app.task
@CaptureTaskLogs("transifex_push")
def transifex_push():
    print("start transifex_push")
    subprocess.run(
        [
            "/app/thinkhazard/scripts/tx-push-db"
        ],
        check=True
    )
    print("end transifex_push")


@app.task
@CaptureTaskLogs("admindivs")
def admindivs():
    print("start admindivis")
    imp.AdministrativeDivisionsImporter.run((INI_FILE, "-v"))
    print("end admindivis")


@app.task
@CaptureTaskLogs("admindivs_gpkg")
def admindivs_gpkg(geopackage_path):
    print("start admindivs_gpkg")
    GeopackageImporter.run((INI_FILE, "-v", "--geopackage-path", geopackage_path))
    print("end admindivs_gpkg")


@app.task
@CaptureTaskLogs("process")
def process():
    print("start processing")
    Harvester.run((INI_FILE, "-v"))
    Downloader.run((INI_FILE, "-v"))
    Completer.run((INI_FILE, "-v"))
    Processor.run((INI_FILE, "-v"))
    DecisionMaker.run((INI_FILE, "-v"))
    print("end processing")
