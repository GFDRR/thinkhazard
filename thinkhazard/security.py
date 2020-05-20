import os
from passlib.apache import HtpasswdFile


def groupfinder(username, password, request):
    ht = HtpasswdFile()
    ht.load_string(os.environ.get("HTPASSWORDS", ""))

    if ht.check_password(username, password):
        return ["admin"]
    else:
        return None
