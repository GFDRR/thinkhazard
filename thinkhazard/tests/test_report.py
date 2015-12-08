from . import BaseTestCase


class TestReportFunction(BaseTestCase):

    def test_report(self):
        self.testapp.get('/report/31', status=200)

    def test_report__division_desecendants(self):
        resp = self.testapp.get('/report/31', status=200)
        # 3 divisions + pin icon
        self.assertEqual(len(resp.pyquery('.breadcrumb .btn')), 4)

        resp = self.testapp.get('/report/10')
        # 1 division + pin icon
        self.assertEqual(len(resp.pyquery('.breadcrumb .btn')), 2)

    def test_report__zoom_out(self):
        resp = self.testapp.get('/report/10')
        # no zoom out for level 1
        self.assertFalse('drillup' in resp.body)

        resp = self.testapp.get('/report/20')
        # zoom out for level > 1
        self.assertTrue('drillup' in resp.body)

    def test_report__hazard_categories(self):
        resp = self.testapp.get('/report/31')
        hazards_list = resp.pyquery('.hazard-types-list')

        # only two categories with data
        self.assertEqual(len(hazards_list.find('li:not(.no-data)')), 2)

        hazards = hazards_list.find('li')

        # order should be 'FL', 'EQ' in icons list
        self.assertTrue('FL' in hazards.eq(0).html())
        self.assertTrue('EQ' in hazards.eq(1).html())

        # whereas order should be 'EQ', 'FL' in overview list
        hazards = resp.pyquery('.overview')
        self.assertTrue('Earthquake' in hazards.eq(0).html())
        self.assertTrue('Flood' in hazards.eq(1).html())

    def test_report__hazard(self):
        resp = self.testapp.get('/report/31/EQ', status=200)
        self.assertTrue('Climate change recommendation' in resp.body)
        self.assertEqual(len(resp.pyquery('.recommendations li')), 2)

    def test_report__further_resources(self):
        resp = self.testapp.get('/report/30/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 1)

        resp = self.testapp.get('/report/31/EQ', status=200)
        self.assertEqual(len(resp.pyquery('.further-resources ul li')), 2)
