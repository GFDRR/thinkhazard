from . import BaseTestCase


class TestIndexFunction(BaseTestCase):

    def test_index(self):
        resp = self.testapp.get('/', status=200)
        hazards = resp.html.select('.hazard-types-list .hazard-icon')
        self.assertEqual(len(hazards), 8)
