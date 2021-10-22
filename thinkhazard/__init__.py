import os
import subprocess

from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound, HTTPUnauthorized
from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.tweens import MAIN
from papyrus.renderers import GeoJSON

from thinkhazard.settings import load_processing_settings, load_local_settings
from thinkhazard.lib.s3helper import S3Helper
from thinkhazard.resources import Root
from thinkhazard.security import groupfinder

try:
    version = subprocess.check_output(
        ["git", "describe", "--always"], cwd=os.path.dirname(__file__)
    )
except Exception:
    version = ""


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """

    load_processing_settings(settings)
    load_local_settings(settings, settings["appname"])
    settings.update({"version": version})

    config = Configurator(root_factory=Root, settings=settings)
    config.set_authorization_policy(
        ACLAuthorizationPolicy()
    )
    config.set_authentication_policy(
        BasicAuthAuthenticationPolicy(
            check=groupfinder,
        )
    )

    # set forbidden view to basic auth
    def forbidden_view(request):
        resp = HTTPUnauthorized()
        resp.www_authenticate = 'Basic realm="Thinkhazard"'
        return resp
    config.add_forbidden_view(forbidden_view)

    config.include("pyramid_jinja2")
    config.include("papyrus")
    config.include("thinkhazard.session")

    config.add_tween("thinkhazard.tweens.set_secure_headers", over=MAIN)
    config.add_tween("thinkhazard.tweens.notmodified_tween_factory", over=MAIN)

    config.add_static_view("static", "thinkhazard:static", cache_max_age=3600)
    config.override_asset(
        to_override="thinkhazard:static/",
        override_with="/opt/thinkhazard/thinkhazard/static",
    )
    config.add_static_view("lib", settings.get("node_modules"), cache_max_age=86000)

    config.add_translation_dirs("thinkhazard:locale")
    config.set_locale_negotiator("thinkhazard.i18n.custom_locale_negotiator")

    config.add_route("healthcheck", "/healthcheck")

    if settings["appname"] == "public":
        config.include(add_public_routes)
        config.add_route("sitemap", "/sitemap.xml")

    if settings["appname"] == "admin":
        # Celery
        from thinkhazard.celery import app as celery_app
        config.add_request_method(lambda x: celery_app, "celery_app", reify=True)

        config.set_default_permission("admin")

        config.include(add_public_routes, route_prefix="preview")

        config.add_route("admin_index", "/")
        config.add_route("admin_add_task", "/addtask")

        config.add_route("admin_technical_rec", "/technical_rec")
        config.add_route("admin_technical_rec_new", "/technical_rec/new")
        config.add_route("admin_technical_rec_edit", "/technical_rec/{id:\d+}")
        config.add_route("admin_technical_rec_delete", "/technical_rec/{id:\d+}/delete")

        config.add_route("admin_admindiv_hazardsets", "/admindiv_hazardsets")
        config.add_route(
            "admin_admindiv_hazardsets_export", "/admindiv_hazardsets_export"
        )
        config.add_route(
            "admin_admindiv_hazardsets_hazardtype",
            "/admindiv_hazardsets/{hazardtype:([A-Z]{2})}",
        )

        config.add_route("admin_climate_rec", "/climate_rec")
        config.add_route(
            "admin_climate_rec_hazardtype", "/climate_rec/{hazard_type:([A-Z]{2})}"
        )
        config.add_route(
            "admin_climate_rec_new", "/climate_rec/{hazard_type:([A-Z]{2})}/new"
        )
        config.add_route("admin_climate_rec_edit", "/climate_rec/{id:\d+}")
        config.add_route("admin_climate_rec_delete", "/climate_rec/{id:\d+}/delete")

        config.add_route("admin_hazardcategories", "/hazardcategories")
        config.add_route(
            "admin_hazardcategory",
            "/hazardcategory/{hazard_type:([A-Z]{2})}" "/{hazard_level:([A-Z]{3})}",
        )

        config.add_route("admin_hazardsets", "/hazardsets")
        config.add_route("admin_hazardset", "/hazardset/{hazardset}")

        config.add_route("admin_contacts", "/contacts")
        config.add_route("admin_contact_new", "/contact/new")
        config.add_route("admin_contact_edit", "/contact/{id:\d+}")
        config.add_route("admin_contact_delete", "/contact/{id:\d+}/delete")
        config.add_route(
            "admin_contact_admindiv_hazardtype_association", "/contact/CAdHt_form"
        )

    config.add_renderer("geojson", GeoJSON())
    config.add_renderer("csv", "thinkhazard.renderers.CSVRenderer")

    config.add_request_method(
        lambda r: S3Helper(r.registry.settings),
        "s3_helper",
        property=True,
        reify=True,
    )

    scan_ignore = []
    if settings["appname"] != "public":
        scan_ignore.append("thinkhazard.views.sitemap")
    if settings["appname"] != "admin":
        scan_ignore.append("thinkhazard.views.admin")
    config.scan(ignore=scan_ignore)

    return config.make_wsgi_app()


def add_public_routes(config):
    add_localized_route(config, "index", "/")
    add_localized_route(config, "about", "/about")
    add_localized_route(config, "faq", "/faq")
    add_localized_route(config, "disclaimer", "/disclaimer")

    def pregenerator(request, elements, kw):
        if "division" in kw:
            division = kw.pop("division")
            kw["divisioncode"] = division.code
            kw["slug"] = "-" + division.slug()
        return elements, kw

    add_localized_route(
        config,
        "report",
        "/report/{divisioncode:\d+}{slug:.*}" "/{hazardtype:([A-Z]{2})}",
        pregenerator=pregenerator,
    )
    add_localized_route(
        config,
        "report_print",
        "/report/print/{divisioncode:\d+}/" "{hazardtype:([A-Z]{2})}",
    )
    add_localized_route(
        config,
        "report_geojson",
        "/report/{divisioncode:\d+}/{hazardtype:([A-Z]{2})}.geojson",
    )
    add_localized_route(
        config,
        "report_neighbours_geojson",
        "/report/{divisioncode:\d+}/neighbours.geojson",
    )
    add_localized_route(
        config, "create_pdf_report", "/report/create/{divisioncode:\d+}"
    )

    add_localized_route(
        config,
        "report_json",
        "/report/{divisioncode:\d+}{slug:.*}/{hazardtype:([A-Z]{2})}.json",
    )
    add_localized_route(
        config, "report_overview_json", "/report/{divisioncode:\d+}{slug:[^.]*}.json"
    )
    add_localized_route(
        config, "report_overview_geojson", "/report/{divisioncode:\d+}.geojson"
    )
    add_localized_route(
        config,
        "report_overview",
        "/report/{divisioncode:\d+}{slug:.*}",
        pregenerator=pregenerator,
    )
    add_localized_route(
        config,
        "report_overview_slash",
        "/report/{divisioncode:\d+}{slug:.*}/",
        pregenerator=pregenerator,
    )

    add_localized_route(config, "administrativedivision", "/administrativedivision")

    add_localized_route(config, "pdf_cover", "/pdf_cover/{divisioncode:\d+}")
    add_localized_route(config, "pdf_about", "/pdf_about")
    add_localized_route(config, "data_source", "/data_source/{hazardset}")
    config.add_route("data_map", "/data_map")

    config.add_route_predicate('languages', LanguagesPredicate)

    add_localized_route(
        config,
        "api_admindiv_hazardsets_hazardtype",
        "/admindiv_hazardsets/{hazardtype:([A-Z]{2})}.json",
    )
    add_localized_route(
        config,
        "api_hazardcategory",
        "/hazardcategory/{hazard_type:([A-Z]{2})}" "/{hazard_level:([A-Z]{3})}.json",
    )


def redirect_to_default_language_factory(route_prefix=None):
    def redirect_to_default_language(request):
        """
        A view that redirects path language-free URLs to the browser prefered
        language or default language URLs.

        E.g. /greeter/foobar -> /en/greeter/foobar
        """
        route = request.matched_route.name.replace("_language_redirect_fallback", "")
        return HTTPFound(request.route_path(route, **request.matchdict))

    return redirect_to_default_language


class LanguagesPredicate():

    def __init__(self, val, config):
        self.val = val

    def text(self):
        return 'languages = %s' % (self.val,)

    phash = text

    def __call__(self, context, request):
        lang = context['match']['lang']
        if lang not in self.val:
            # Redirect to default language
            raise HTTPFound(
                request.route_url(
                    context['route'].name,
                    **{
                        **context['match'],
                        "lang": request.registry.settings["default_locale_name"],
                    }
                )
            )

        request.response.set_cookie(
            "_LOCALE_", value=lang, max_age=20 * 7 * 24 * 60 * 60
        )
        request.locale_name = lang
        return True


def add_localized_route(config, name, pattern, pregenerator=None, **kw):
    """
    Create path language aware routing paths.

    Each route will have /{lang}/ prefix added to them.

    Optionally, if default language is set, we'll create redirect from an URL
    without language path component to the URL with the language path
    component.
    """
    orig_pregenerator = pregenerator

    def wrapper_pregenerator(request, elements, kw):
        if "lang" not in kw:
            kw["lang"] = (
                request.locale_name or config.registry.settings["default_locale_name"]
            )
        if orig_pregenerator:
            return orig_pregenerator(request, elements, kw)
        return elements, kw

    if pattern.startswith("/"):
        new_pattern = pattern[1:]
    else:
        new_pattern = pattern

    new_pattern = "/{lang}/" + new_pattern

    # Language-aware URL routed
    config.add_route(
        name,
        new_pattern,
        pregenerator=wrapper_pregenerator,
        languages=config.registry.settings["available_languages"].split(),
        **kw
    )

    # Add redirect to the default language routes
    fallback_route_name = name + "_language_redirect_fallback"
    config.add_route(fallback_route_name, pattern)
    config.add_view(
        redirect_to_default_language_factory(config.route_prefix),
        route_name=fallback_route_name,
    )
