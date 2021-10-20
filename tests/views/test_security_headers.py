from . import BaseTestCase


class TestAdminSecurityHeaders(BaseTestCase):

    app_name = "admin"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.testapp.authorization = ('Basic', ('admin', 'admin'))

    def test_index(self):
        resp = self.testapp.get("/", status=200)

        for key, value in (
            ('Cache-Control', 'no-store'),
            # ('Content-Length', '4875'),
            (
                'Content-Security-Policy',
                "default-src 'self';"
                " script-src 'self' 'unsafe-inline' https://www.google-analytics.com https://cdnjs.cloudflare.com;"
                " style-src 'self' https://fonts.googleapis.com;"
                " font-src 'self' https://fonts.gstatic.com;"
                " img-src 'self' data: https://www.gfdrr.org http://www.geonode-gfdrrlab.org https://api.mapbox.com;"
                " connect-src 'self' https://www.google-analytics.com"
            ),
            ('Content-Type', 'text/html; charset=UTF-8'),
            # ('Expires', 'Thu, 21 Oct 2021 08:44:00 GMT'),
            # ('Last-Modified', 'Thu, 21 Oct 2021 08:44:00 GMT'),
            ('Pragma', 'no-cache'),
            ('Referrer-Policy', 'no-referrer, strict-origin-when-cross-origin'),
            ('Strict-Transport-Security', 'max-age=31536000; includeSubDomains'),
            ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'SAMEORIGIN'),
            ('X-XSS-Protection', '0'),
        ):
            assert value in resp.headers.getall(key), "key {} is not {} but {}".format(key, value, resp.headers.getall(key))


class TestPublicSecurityHeaders(BaseTestCase):

    app_name = "public"

    def test_index(self):
        resp = self.testapp.get("/en/", status=200)

        for key, value in (
            ('Cache-Control', 'public'),
            # ('Content-Length', '9455'),
            (
                'Content-Security-Policy',
                "default-src 'self';"
                " script-src 'self' 'unsafe-inline' https://www.google-analytics.com https://cdnjs.cloudflare.com;"
                " style-src 'self' https://fonts.googleapis.com;"
                " font-src 'self' https://fonts.gstatic.com;"
                " img-src 'self' data: https://www.gfdrr.org http://www.geonode-gfdrrlab.org https://api.mapbox.com;"
                " connect-src 'self' https://www.google-analytics.com"
            ),
            ('Content-Type', 'text/html; charset=UTF-8'),
            # ('Last-Modified', 'Thu, 21 Oct 2021 08:48:36 GMT'),
            ('Referrer-Policy', 'no-referrer, strict-origin-when-cross-origin'),
            ('Strict-Transport-Security', 'max-age=31536000; includeSubDomains'),
            ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'SAMEORIGIN'),
            ('X-XSS-Protection', '0'),
        ):
            assert value in resp.headers.getall(key), "key {} is not {} but {}".format(key, value, resp.headers.getall(key))
