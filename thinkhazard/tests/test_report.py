from . import BaseTestCase


class TestReportFunction(BaseTestCase):

    def test_report(self):
        self.testapp.get('/report/30', status=200)

    def test_report__division_desecendants(self):
        resp = self.testapp.get('/report/30', status=200)
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
        resp = self.testapp.get('/report/30')
        hazards_list = resp.pyquery('.hazard-types-list')

        # only two categories with data
        self.assertEqual(len(hazards_list.find('li:not(.no-data)')), 2)

        hazards = hazards_list.find('li')

        # order should be 'FL', 'EQ'
        self.assertTrue('FL' in hazards.eq(0).html())
        self.assertTrue('EQ' in hazards.eq(1).html())

    def test_report__hazard(self):
        resp = self.testapp.get('/report/30/EQ', status=200)
        #self.assertEqual(len(resp.pyquery('.recommendations li')), 1)
        #self.assertEqual(len(resp.pyquery('.further-resources li')), 1)
