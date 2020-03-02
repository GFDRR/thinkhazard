# myapp/lib/pshell.py
from contextlib import suppress
from transaction.interfaces import NoTransaction

def setup(env):
    request = env['request']

    request.tm.begin()

    env['tm'] = request.tm
    env['s'] = request.dbsession
    try:
        yield

    finally:
        with suppress(NoTransaction):
            request.tm.abort()

