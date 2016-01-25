from . import BaseTestCase


class TestSearchFunction(BaseTestCase):

    def test_search(self):
        resp = self.testapp.get('/administrativedivision', dict(q='Division'),
                                status=200)
        self.assertEqual(len(resp.json['data']), 4)
