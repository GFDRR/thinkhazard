import importlib
import io
import codecs
import logging
import traceback
import os
import subprocess
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


def capture_task_logs(task_name, func, *args, **kwargs):
    """Capture logs during task execution and upload to S3."""
    settings = load_full_settings(INI_FILE, name="admin")

    bytes_log = io.BytesIO()
    stream_writer = codecs.getwriter("utf-8")
    str_log = stream_writer(bytes_log)
    log_handler = logging.StreamHandler(str_log)
    log_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
    log_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)

    try:
        result = func(*args, **kwargs)
        return result
    except Exception as e:
        root_logger.error(f"Task {task_name} failed with error: {e}")
        root_logger.error(traceback.format_exc())
        raise
    finally:
        root_logger.removeHandler(log_handler)
        bytes_log.seek(0)

        try:
            s3_helper = S3Helper(settings)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"logs/{task_name}_{timestamp}.txt"
            s3_helper.upload_fileobj(bytes_log, object_name)
        except Exception as e:
            print(f"Failed to upload log to S3: {e}")


def _run_publish():
    print("start publish")
    Publisher.run((INI_FILE, "-v"))
    print("end publish")


def _run_transifex_fetch():
    print("start transifex_fetch")
    subprocess.run(
        [
            "/app/thinkhazard/scripts/tx-pull-db"
        ],
        check=True
    )
    print("end transifex_fetch")


def _run_transifex_push():
    print("start transifex_push")
    subprocess.run(
        [
            "/app/thinkhazard/scripts/tx-push-db"
        ],
        check=True
    )
    print("end transifex_push")


def _run_admindivs():
    print("start admindivis")
    imp.AdministrativeDivisionsImporter.run((INI_FILE, "-v"))
    print("end admindivis")


def _run_admindivs_gpkg(geopackage_path):
    print("start admindivs_gpkg")
    GeopackageImporter.run((INI_FILE, "-v", "--geopackage-path", geopackage_path))
    print("end admindivs_gpkg")


def _run_process():
    print("start processing")
    Harvester.run((INI_FILE, "-v"))
    Downloader.run((INI_FILE, "-v"))
    Completer.run((INI_FILE, "-v"))
    Processor.run((INI_FILE, "-v"))
    DecisionMaker.run((INI_FILE, "-v"))
    print("end processing")


@app.task
def publish():
    capture_task_logs("publish", _run_publish)


@app.task
def transifex_fetch():
    capture_task_logs("transifex_fetch", _run_transifex_fetch)


@app.task
def transifex_push():
    capture_task_logs("transifex_push", _run_transifex_push)


@app.task
def admindivs():
    capture_task_logs("admindivs", _run_admindivs)


@app.task
def admindivs_gpkg(geopackage_path):
    capture_task_logs("admindivs_gpkg", _run_admindivs_gpkg, geopackage_path)


@app.task
def process():
    capture_task_logs("process", _run_process)
