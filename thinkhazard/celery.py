import importlib
import os
import time
from celery import Celery

imp = importlib.import_module("thinkhazard.processing.import")

INI_FILE = os.environ["INI_FILE"]

app = Celery()
app.conf.broker_url = os.environ["BROKER_URL"]
app.conf.result_backend = 's3'
app.conf.s3_bucket = 'thinkhazard'
app.conf.s3_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
app.conf.s3_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
app.conf.s3_bucket = os.environ["AWS_BUCKET_NAME"]
app.conf.s3_region = 'eu-west-1'


@app.task
def publish():
    print("start publish")
    time.sleep(10)
    print("end publish")

@app.task
def transifex_fetch():
    print("start pull/import from transifex")
    time.sleep(10)
    print("end pull/import from transifex")

@app.task
def admindivs():
    print("start import administrative divisions")
    print(INI_FILE)
    imp.AdministrativeDivisionsImporter.run((INI_FILE,))
    print("end import administrative divisions")
