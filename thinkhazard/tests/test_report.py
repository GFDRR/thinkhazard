from . import BaseTestCase


class TestReportFunction(BaseTestCase):

    def test_report(self):
        resp = self.testapp.get('/report/30', status=200)
