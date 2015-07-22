import unittest
import transaction
import os

from pyramid import testing

from ..models import DBSession

local_settings_path = 'local.tests.ini'

# raise an error if the config file doesn't exists
with open(local_settings_path):
    pass


class TestIndexFunction(unittest.TestCase):

    def setUp(self):
        from .. import main
        from webtest import TestApp
        from paste.deploy import loadapp

        conf_dir = os.getcwd()
        self.app = loadapp('config:tests.ini', relative_to=conf_dir)
        self.testapp = TestApp(self.app)

    def tearDown(self):
        del self.app
        del self.testapp

    def test_index(self):
        print "blah"
        self.testapp.get('/', status=200)
