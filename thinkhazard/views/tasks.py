from pyramid_celery import celery_app as app
import time

@app.task
def process(name):
    print('start task: {}'.format(name))
    time.sleep(10)
    print('end task: {}'.format(name))
