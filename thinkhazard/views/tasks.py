from pyramid_celery import celery_app as app
import importlib
import os
import time

imp = importlib.import_module("thinkhazard.processing.import")

INI_FILE = os.environ["INI_FILE"]


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
