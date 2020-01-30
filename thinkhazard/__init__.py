import os
import subprocess

from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPFound
from sqlalchemy import engine_from_config
from papyrus.renderers import GeoJSON

from .settings import load_processing_settings, load_local_settings
from .models import DBSession, Base

lock_file = os.path.join(os.path.dirname(__file__), "maintenance.lock")


try:
    version = subprocess.check_output(
        ["git", "describe", "--always"], cwd=os.path.dirname(__file__)
    )
except Exception as e:
    version = ""


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """

    load_processing_settings(settings)
    load_local_settings(settings, settings["appname"])
    settings.update({"version": version})

    engine = engine_from_config(settings, "sqlalchemy.")
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings)

    config.include("pyramid_jinja2")
    config.include("papyrus")

    config.add_tween("thinkhazard.tweens.notmodified_tween_factory")

    config.add_static_view("static", "static", cache_max_age=3600)
    config.add_static_view("lib", settings.get("node_modules"), cache_max_age=86000)

    config.add_translation_dirs("thinkhazard:locale")
    config.set_locale_negotiator("thinkhazard.i18n.custom_locale_negotiator")

    if settings["appname"] == "public":
        config.include(add_public_routes)
        config.add_route("sitemap", "/sitemap.xml")

    if settings["appname"] == "admin":
        config.include(add_public_routes, route_prefix="preview")

        config.add_route("admin_index", "/")

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

    scan_ignore = ["thinkhazard.tests"]
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
        config, "get_report_status", "/report/status/{divisioncode:\d+}/{id}.json"
    )
    add_localized_route(config, "get_pdf_report", "/report/{divisioncode:\d+}/{id}.pdf")
    add_localized_route(config, "get_map_report", "/report/map.jpg")

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


def add_localized_route(config, name, pattern, factory=None, pregenerator=None, **kw):
    """
    Create path language aware routing paths.

    Each route will have /{lang}/ prefix added to them.

    Optionally, if default language is set, we'll create redirect from an URL
    without language path component to the URL with the language path
    component.
    """
    orig_factory = factory

    def wrapper_factory(request):
        lang = request.matchdict["lang"]
        # determine if this is a supported lang and convert it to a locale,
        # likely defaulting to your default language if the requested one is
        # not supported by your app
        if lang not in request.registry.settings['available_languages'].split():
            raise HTTPFound(
                request.current_route_url(
                    lang=request.registry.settings['default_locale_name']
                )
            )

        request.response.set_cookie(
            "_LOCALE_", value=lang, max_age=20 * 7 * 24 * 60 * 60
        )
        request.locale_name = lang

        if orig_factory:
            return orig_factory(request)

    orig_pregenerator = pregenerator

    def wrapper_pregenerator(request, elements, kw):
        if "lang" not in kw:
            kw["lang"] = (
                request.locale_name or config.registry.settings['default_locale_name']
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
        factory=wrapper_factory,
        pregenerator=wrapper_pregenerator,
        **kw
    )

    # Add redirect to the default language routes
    fallback_route_name = name + "_language_redirect_fallback"
    config.add_route(fallback_route_name, pattern)
    config.add_view(
        redirect_to_default_language_factory(config.route_prefix),
        route_name=fallback_route_name,
    )
