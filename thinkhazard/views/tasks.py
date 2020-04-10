from pyramid_celery import celery_app as app
import time

@app.task
def publish():
    print('start publish')
    time.sleep(10)
    print('end publish')
