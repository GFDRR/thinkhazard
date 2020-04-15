# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 by the GFDRR / World Bank
#
# This file is part of ThinkHazard.
#
# ThinkHazard is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# ThinkHazard is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# ThinkHazard.  If not, see <http://www.gnu.org/licenses/>.

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest
from sqlalchemy import func, inspect, Integer
from sqlalchemy.orm import contains_eager, joinedload
from pyramid_celery import celery_app as app
import json
from datetime import datetime

from thinkhazard.models import (
    AdminLevelType,
    AdministrativeDivision,
    Contact,
    ContactAdministrativeDivisionHazardTypeAssociation as CAdHt,
    ClimateChangeRecommendation,
    ClimateChangeRecAdministrativeDivisionAssociation as CcrAd,
    HazardCategory,
    HazardCategoryTechnicalRecommendationAssociation as HcTr,
    HazardCategoryAdministrativeDivisionAssociation,
    HazardLevel,
    HazardType,
    HazardSet,
    Layer,
    TechnicalRecommendation,
    Publication,
)
import thinkhazard.views.tasks as tasks

TASKS_LABELS = {
    "publish": "Publication",
    "transifex_fetch": "Import from Transifex",
    "admindivs": "Import administrative division from GeoNode",
}


@view_config(route_name="admin_index", renderer="templates/admin/index.jinja2")
def index(request):
    tasks = list(app.control.inspect().active().values())[0]
    for t in tasks:
        t["time_label"] = datetime.fromtimestamp(t["time_start"]).strftime(
            "%a, %d %b %Y %H:%M"
        )
        t["name"] = t["name"].split(".").pop()
        t["label"] = TASKS_LABELS[t["name"]]
    return {
        "publication_date": Publication.last(request.dbsession).date,
        "running": tasks,
        "running_keys": list(map(lambda t: t["name"], tasks)),
    }


@view_config(route_name="admin_add_task")
def add_task(request):
    task = request.params.get("task")
    getattr(tasks, task).delay()
    return HTTPFound(request.route_url("admin_index"))


@view_config(
    route_name="admin_hazardcategories",
    renderer="templates/admin/hazardcategories.jinja2",
)
def hazardcategories(request):
    hazard_types = request.dbsession.query(HazardType).order_by(HazardType.order)
    hazard_levels = []
    for level in ["HIG", "MED", "LOW", "VLO"]:
        hazard_levels.append(HazardLevel.get(request.dbsession, level))
    return {"hazard_types": hazard_types, "hazard_levels": hazard_levels}


@view_config(
    route_name="admin_hazardcategory", renderer="templates/admin/hazardcategory.jinja2"
)
def hazardcategory(request):
    hazard_type = request.matchdict["hazard_type"]
    hazard_level = request.matchdict["hazard_level"]

    if request.method == "GET":
        hazard_category = (
            request.dbsession.query(HazardCategory)
            .join(HazardType)
            .join(HazardLevel)
            .filter(HazardType.mnemonic == hazard_type)
            .filter(HazardLevel.mnemonic == hazard_level)
            .one()
        )
        if hazard_category is None:
            raise HTTPNotFound()

        associations = (
            request.dbsession.query(HcTr)
            .filter(HcTr.hazardcategory_id == hazard_category.id)
            .order_by(HcTr.order)
            .all()
        )

        return {
            "action": request.route_url(
                "admin_hazardcategory",
                hazard_type=hazard_type,
                hazard_level=hazard_level,
            ),
            "hazard_category": hazard_category,
            "associations": associations,
        }

    if request.method == "POST":
        hazard_category = request.dbsession.query(HazardCategory).get(
            request.POST.get("id")
        )
        if hazard_category is None:
            raise HTTPNotFound()

        hazard_category.general_recommendation = request.POST.get(
            "general_recommendation"
        )

        associations = request.POST.getall("associations")
        order = 0
        for association_id in associations:
            order += 1
            association = request.dbsession.query(HcTr).get(association_id)
            association.order = order
        return HTTPFound(
            request.route_url(
                "admin_hazardcategory",
                hazard_type=hazard_type,
                hazard_level=hazard_level,
            )
        )


@view_config(
    route_name="admin_technical_rec",
    renderer="templates/admin/technical_rec_index.jinja2",
)
def technical_rec(request):
    technical_recs = (
        request.dbsession.query(TechnicalRecommendation)
        .order_by(TechnicalRecommendation.text)
        .all()
    )
    for technical_rec in technical_recs:
        technical_rec.hazardcategories = ", ".join(
            [
                association.hazardcategory.name()
                for association in technical_rec.hazardcategory_associations
            ]
        )
    return {"technical_recs": technical_recs}


@view_config(
    route_name="admin_technical_rec_new",
    renderer="templates/admin/technical_rec_form.jinja2",
)
def technical_rec_new(request):
    obj = TechnicalRecommendation()
    return technical_rec_process(request, obj)


@view_config(
    route_name="admin_technical_rec_edit",
    renderer="templates/admin/technical_rec_form.jinja2",
)
def technical_rec_edit(request):
    id = request.matchdict["id"]
    obj = request.dbsession.query(TechnicalRecommendation).get(id)
    if obj is None:
        raise HTTPNotFound()
    return technical_rec_process(request, obj)


@view_config(route_name="admin_technical_rec_delete")
def technical_rec_delete(request):
    id = request.matchdict["id"]
    obj = request.dbsession.query(TechnicalRecommendation).get(id)
    request.dbsession.delete(obj)
    return HTTPFound(request.route_url("admin_technical_rec"))


def technical_rec_process(request, obj):
    if request.method == "GET":
        hazard_types = request.dbsession.query(HazardType).order_by(HazardType.order)
        hazard_levels = []
        for level in ["HIG", "MED", "LOW", "VLO"]:
            hazard_levels.append(HazardLevel.get(request.dbsession, level))
        if obj.id is None:
            action = request.route_url("admin_technical_rec_new")
        else:
            action = request.route_url("admin_technical_rec_edit", id=obj.id)
        return {
            "obj": obj,
            "action": action,
            "hazard_types": hazard_types,
            "hazard_levels": hazard_levels,
        }

    if request.method == "POST":
        obj.text = request.POST.get("text")
        obj.detail = request.POST.get("detail")
        if inspect(obj).transient:
            request.dbsession.add(obj)

        associations = request.POST.getall("associations")
        records = obj.hazardcategory_associations

        # Remove unchecked ones
        for record in records:
            if record.hazardcategory.name() not in associations:
                request.dbsession.delete(record)

        # Add new ones
        for association in associations:
            hazardtype, hazardlevel = association.split(" - ")
            if not obj.has_association(hazardtype, hazardlevel):
                hazardcategory = HazardCategory.get(
                    request.dbsession, hazardtype, hazardlevel
                )
                order = (
                    request.dbsession.query(
                        func.coalesce(func.cast(func.max(HcTr.order), Integer), 0)
                    )
                    .select_from(HcTr)
                    .filter(HcTr.hazardcategory_id == hazardcategory.id)
                    .first()[0]
                    + 1
                )

                record = HcTr(hazardcategory=hazardcategory, order=order)
                obj.hazardcategory_associations.append(record)

        request.dbsession.flush()
        return HTTPFound(request.route_url("admin_technical_rec"))


@view_config(
    route_name="admin_hazardsets", renderer="templates/admin/hazardsets.jinja2"
)
def hazardsets(request):
    return {"hazardsets": request.dbsession.query(HazardSet).order_by(HazardSet.id)}


@view_config(route_name="admin_hazardset", renderer="templates/admin/hazardset.jinja2")
def hazardset(request):
    id = request.matchdict["hazardset"]
    hazardset = (
        request.dbsession.query(HazardSet)
        .options(joinedload(HazardSet.layers).joinedload(Layer.hazardlevel))
        .get(id)
    )
    return {"hazardset": hazardset}


@view_config(route_name="admin_admindiv_hazardsets")
def admindiv_hazardsets(request):
    hazardtype = request.dbsession.query(HazardType).first()
    return HTTPFound(
        request.route_url(
            "admin_admindiv_hazardsets_hazardtype", hazardtype=hazardtype.mnemonic
        )
    )


@view_config(
    route_name="admin_admindiv_hazardsets_hazardtype",
    renderer="templates/admin/admindiv_hazardsets.jinja2",
)
def admin_admindiv_hazardsets_hazardtype(request):
    data = admindiv_hazardsets_hazardtype(request)
    hazard_types = request.dbsession.query(HazardType).order_by(HazardType.order).all()
    return {"hazard_types": hazard_types, "data": json.dumps(data)}


def admindiv_hazardsets_hazardtype(request):

    try:
        hazardtype = request.matchdict.get("hazardtype")
    except:
        raise HTTPBadRequest(detail="incorrect value for parameter " '"hazardtype"')

    if HazardType.get(request.dbsession, hazardtype) is None:
        raise HTTPBadRequest(detail="hazardtype doesn't exist")

    query = (
        request.dbsession.query(AdministrativeDivision)
        .join(HazardCategoryAdministrativeDivisionAssociation)
        .join(HazardCategory)
        .join(HazardType)
        .filter(HazardType.mnemonic == hazardtype)
        .join(AdminLevelType)
        .filter(AdminLevelType.id == 3)
        .order_by(AdministrativeDivision.name)
        .options(contains_eager(AdministrativeDivision.hazardcategories))
    )

    data = [
        {
            "code": row.code,
            "name": row.name,
            "level_2": row.parent.name,
            "level_1": row.parent.parent.name,
            "hazardset": row.hazardcategories[0].hazardsets[0].id
            if row.hazardcategories[0].hazardsets
            else None,
            "hazard_level": row.hazardcategories[0].hazardcategory.hazardlevel.mnemonic,
        }
        for row in query
    ]

    return data


@view_config(route_name="admin_admindiv_hazardsets_export", renderer="csv")
def admindiv_hazardsets_export(request):
    query = """SELECT ht.mnemonic, ad.id, ad.name, hl.mnemonic
    FROM processing.output AS o LEFT JOIN datamart.administrativedivision
    AS ad ON o.admin_id = ad.id LEFT JOIN datamart.enum_hazardlevel hl ON
    o.hazardlevel_id = hl.id LEFT JOIN processing.hazardset AS hs ON
    o.hazardset_id = hs.id LEFT JOIN datamart.enum_hazardtype AS ht ON
    hs.hazardtype_id = ht.id WHERE ad.leveltype_id = 3
    ORDER BY ht.mnemonic, ad.name"""
    rows = request.dbsession.execute(query)

    return {"headers": ["hazardtype", "code", "name", "hazard_level"], "rows": rows}


@view_config(route_name="admin_climate_rec")
def climate_rec(request):
    hazardtype = request.dbsession.query(HazardType).first()
    return HTTPFound(
        request.route_url(
            "admin_climate_rec_hazardtype", hazard_type=hazardtype.mnemonic
        )
    )


@view_config(
    route_name="admin_climate_rec_hazardtype",
    renderer="templates/admin/climate_rec_index.jinja2",
)
def climate_rec_hazardtype(request):
    hazard_type = request.matchdict["hazard_type"]
    hazardtype = HazardType.get(request.dbsession, hazard_type)
    if hazardtype is None:
        raise HTTPNotFound

    hazard_types = request.dbsession.query(HazardType).order_by(HazardType.order)

    climate_recs = request.dbsession.query(ClimateChangeRecommendation).filter(
        ClimateChangeRecommendation.hazardtype == hazardtype
    )
    return {"hazard_types": hazard_types, "climate_recs": climate_recs}


@view_config(
    route_name="admin_climate_rec_new",
    renderer="templates/admin/climate_rec_form.jinja2",
)
def climate_rec_new(request):
    hazard_type = request.matchdict["hazard_type"]
    hazardtype = HazardType.get(request.dbsession, hazard_type)
    if hazardtype is None:
        raise HTTPNotFound

    obj = ClimateChangeRecommendation()
    obj.hazardtype = hazardtype
    return climate_rec_process(request, obj)


@view_config(
    route_name="admin_climate_rec_edit",
    renderer="templates/admin/climate_rec_form.jinja2",
)
def climate_rec_edit(request):
    id = request.matchdict["id"]
    obj = request.dbsession.query(ClimateChangeRecommendation).get(id)
    if obj is None:
        raise HTTPNotFound()
    return climate_rec_process(request, obj)


@view_config(route_name="admin_climate_rec_delete")
def climate_rec_delete(request):
    id = request.matchdict["id"]
    obj = request.dbsession.query(ClimateChangeRecommendation).get(id)
    request.dbsession.delete(obj)
    return HTTPFound(
        request.route_url(
            "admin_climate_rec_hazardtype", hazard_type=obj.hazardtype.mnemonic
        )
    )


def climate_rec_process(request, obj):
    if request.method == "GET":
        hazard_types = request.dbsession.query(HazardType).order_by(HazardType.order)

        association_subq = (
            request.dbsession.query(CcrAd)
            .filter(CcrAd.hazardtype == obj.hazardtype)
            .subquery()
        )

        admin_divs = (
            request.dbsession.query(AdministrativeDivision, ClimateChangeRecommendation)
            .select_from(AdministrativeDivision)
            .outerjoin(
                association_subq,
                association_subq.c.administrativedivision_id
                == AdministrativeDivision.id,
            )
            .outerjoin(
                ClimateChangeRecommendation,
                ClimateChangeRecommendation.id
                == association_subq.c.climatechangerecommendation_id,
            )
            .join(AdminLevelType)
            .filter(AdminLevelType.mnemonic == "COU")
            .order_by(AdministrativeDivision.name)
        )

        if obj.id is None:
            action = request.route_url(
                "admin_climate_rec_new", hazard_type=obj.hazardtype.mnemonic
            )
        else:
            action = request.route_url("admin_climate_rec_edit", id=obj.id)
        return {
            "obj": obj,
            "action": action,
            "hazard_types": hazard_types,
            "admin_divs": admin_divs,
        }

    if request.method == "POST":
        if inspect(obj).transient:
            request.dbsession.add(obj)

        obj.hazardtype = HazardType.get(
            request.dbsession, request.POST.get("hazard_type")
        )
        obj.text = request.POST.get("text")

        admindiv_ids = request.POST.getall("associations")

        # Remove unchecked ones
        for association in obj.associations:
            if association.administrativedivision_id not in admindiv_ids:
                request.dbsession.delete(association)

        # Add new ones
        for admindiv_id in admindiv_ids:
            association = request.dbsession.query(CcrAd).get(
                (admindiv_id, obj.hazardtype.id)
            )
            if association is None:
                association = CcrAd(
                    administrativedivision_id=admindiv_id, hazardtype=obj.hazardtype
                )
                obj.associations.append(association)
            else:
                association.climatechangerecommendation = obj

        request.dbsession.flush()
        return HTTPFound(
            request.route_url("admin_climate_rec_edit", id=obj.hazardtype.mnemonic)
        )


@view_config(
    route_name="admin_contacts", renderer="templates/admin/contact_index.jinja2"
)
def contacts(request):
    return {"contacts": request.dbsession.query(Contact).order_by(Contact.name)}


@view_config(
    route_name="admin_contact_new", renderer="templates/admin/contact_form.jinja2"
)
def contact_new(request):
    obj = Contact()
    return contact_process(request, obj)


@view_config(
    route_name="admin_contact_edit", renderer="templates/admin/contact_form.jinja2"
)
def contact_edit(request):
    id = request.matchdict["id"]
    obj = request.dbsession.query(Contact).get(id)
    if obj is None:
        raise HTTPNotFound()
    return contact_process(request, obj)


@view_config(route_name="admin_contact_delete")
def contact_delete(request):
    id = request.matchdict["id"]
    obj = request.dbsession.query(Contact).get(id)
    if obj is None:
        raise HTTPNotFound()
    for association in obj.associations:
        request.dbsession.delete(association)
    request.dbsession.delete(obj)
    return HTTPFound(request.route_url("admin_contacts"))


def contact_process(request, obj):
    if request.method == "GET":
        if obj.id is None:
            action = request.route_url("admin_contact_new")
        else:
            action = request.route_url("admin_contact_edit", id=obj.id)

        countries = (
            request.dbsession.query(AdministrativeDivision)
            .join(AdminLevelType)
            .filter(AdminLevelType.mnemonic == "COU")
            .order_by(AdministrativeDivision.name)
        )

        hazard_types = request.dbsession.query(HazardType).order_by(HazardType.order)

        associations = request.dbsession.query(CAdHt).filter(CAdHt.contact_id == obj.id)

        return {
            "obj": obj,
            "action": action,
            "countries": countries,
            "hazard_types": hazard_types,
            "associations": associations,
        }

    if request.method == "POST":
        obj.name = request.POST.get("name")
        obj.phone = request.POST.get("phone")
        obj.url = request.POST.get("url")
        obj.email = request.POST.get("email")

        request.dbsession.query(CAdHt).filter(CAdHt.contact_id == obj.id).delete()
        countries = request.POST.getall("country")
        hazard_types = request.POST.getall("hazard_type")
        for i in range(0, len(countries)):
            association = CAdHt(
                contact=obj,
                administrativedivision_id=int(countries[i]),
                hazardtype_id=int(hazard_types[i]),
            )
            request.dbsession.add(association)

        if inspect(obj).transient:
            request.dbsession.add(obj)

        request.dbsession.flush()
        return HTTPFound(request.route_url("admin_contacts"))


@view_config(
    route_name="admin_contact_admindiv_hazardtype_association",
    renderer="templates/admin/CAdHt_form.jinja2",
)
def contact_admindiv_hazardtype_association(request):

    countries = (
        request.dbsession.query(AdministrativeDivision)
        .join(AdminLevelType)
        .filter(AdminLevelType.mnemonic == "COU")
        .order_by(AdministrativeDivision.name)
    )

    hazard_types = request.dbsession.query(HazardType).order_by(HazardType.order)

    return {"countries": countries, "hazard_types": hazard_types}
