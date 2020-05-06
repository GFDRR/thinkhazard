import importlib
import os
import time
from celery import Celery

from thinkhazard.processing.harvesting import Harvester
from thinkhazard.processing.downloading import Downloader
from thinkhazard.processing.completing import Completer
from thinkhazard.processing.processing import Processor
from thinkhazard.processing.decisiontree import DecisionMaker
from thinkhazard.scripts.publish import main as publish_main
imp = importlib.import_module("thinkhazard.processing.import")

INI_FILE = os.environ["INI_FILE"]

app = Celery()
app.conf.broker_url = os.environ["BROKER_URL"]
app.conf.result_backend = "s3"
app.conf.s3_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
app.conf.s3_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
app.conf.s3_bucket = os.environ["AWS_BUCKET_NAME"]
app.conf.s3_region = "eu-west-1"


@app.task
def publish():
    print("start publish")
    publish_main(argv=(None, INI_FILE.strip("'")))
    print("end publish")


@app.task
def transifex_fetch():
    print("start transifex_fetch")
    # FIXME plug to real task
    time.sleep(10)
    print("end transifex_fetch")


@app.task
def admindivs():
    print("start admindivis")
    imp.AdministrativeDivisionsImporter.run((INI_FILE,))
    print("end admindivis")


@app.task
def process():
    print("start processing")
    Harvester.run((INI_FILE,))
    Downloader.run((INI_FILE,))
    Completer.run((INI_FILE,))
    Processor.run((INI_FILE,))
    DecisionMaker.run((INI_FILE,))
    print("end processing")
