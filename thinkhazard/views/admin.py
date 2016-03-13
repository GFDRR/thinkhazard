from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    HTTPBadRequest,
    )

from sqlalchemy import (
    func,
    inspect,
    Integer,
    )

from sqlalchemy.orm import contains_eager, joinedload

import json

from ..models import (
    DBSession,
    AdminLevelType,
    AdministrativeDivision,
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
    )


@view_config(route_name='admin_index',
             renderer='templates/admin/index.jinja2')
def index(request):
    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    hazard_levels = []
    for level in [u'HIG', u'MED', u'LOW', u'VLO']:
        hazard_levels.append(HazardLevel.get(level))
    return {
        'hazard_types': hazard_types,
        'hazard_levels': hazard_levels,
        }


@view_config(route_name='admin_hazardcategory',
             renderer='templates/admin/hazardcategory.jinja2')
def hazardcategory(request):
    hazard_type = request.matchdict['hazard_type']
    hazard_level = request.matchdict['hazard_level']

    if request.method == 'GET':
        hazard_category = DBSession.query(HazardCategory) \
            .join(HazardType) \
            .join(HazardLevel) \
            .filter(HazardType.mnemonic == hazard_type) \
            .filter(HazardLevel.mnemonic == hazard_level) \
            .one()
        if hazard_category is None:
            raise HTTPNotFound()

        associations = DBSession.query(HcTr) \
            .filter(HcTr.hazardcategory_id == hazard_category.id) \
            .order_by(HcTr.order) \
            .all()

        return {
            'action': request.route_url('admin_hazardcategory',
                                        hazard_type=hazard_type,
                                        hazard_level=hazard_level),
            'hazard_category': hazard_category,
            'associations': associations
            }

    if request.method == 'POST':
        hazard_category = DBSession.query(HazardCategory) \
            .get(request.POST.get('id'))
        if hazard_category is None:
            raise HTTPNotFound()

        hazard_category.general_recommendation = \
            request.POST.get('general_recommendation')

        associations = request.POST.getall('associations')
        order = 0
        for association_id in associations:
            order += 1
            association = DBSession.query(HcTr).get(association_id)
            association.order = order
        return HTTPFound(request.route_url('admin_hazardcategory',
                                           hazard_type=hazard_type,
                                           hazard_level=hazard_level))


@view_config(route_name='admin_technical_rec',
             renderer='templates/admin/technical_rec_index.jinja2')
def technical_rec(request):
    technical_recs = DBSession.query(TechnicalRecommendation) \
        .all()
    for technical_rec in technical_recs:
        technical_rec.hazardcategories = \
            ', '.join([association.hazardcategory.name() for association in
                       technical_rec.hazardcategory_associations])
    return {
        'technical_recs': technical_recs,
        'test': [str(x) for x in xrange(10)],
        }


@view_config(route_name='admin_technical_rec_new',
             renderer='templates/admin/technical_rec_form.jinja2')
def technical_rec_new(request):
    obj = TechnicalRecommendation()
    return technical_rec_process(request, obj)


@view_config(route_name='admin_technical_rec_edit',
             renderer='templates/admin/technical_rec_form.jinja2')
def technical_rec_edit(request):
    id = request.matchdict['id']
    obj = DBSession.query(TechnicalRecommendation).get(id)
    if obj is None:
        raise HTTPNotFound()
    return technical_rec_process(request, obj)


def technical_rec_process(request, obj):
    if request.method == 'GET':
        hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
        hazard_levels = []
        for level in [u'HIG', u'MED', u'LOW', u'VLO']:
            hazard_levels.append(HazardLevel.get(level))
        if obj.id is None:
            action = request.route_url('admin_technical_rec_new')
        else:
            action = request.route_url('admin_technical_rec_edit', id=obj.id)
        return {
            'obj': obj,
            'action': action,
            'hazard_types': hazard_types,
            'hazard_levels': hazard_levels,
        }

    if request.method == 'POST':
        obj.text = request.POST.get('text')
        if inspect(obj).transient:
            DBSession.add(obj)

        associations = request.POST.getall('associations')
        records = obj.hazardcategory_associations

        # Remove unchecked ones
        for record in records:
            if record.hazardcategory.name() not in associations:
                DBSession.delete(record)

        # Add new ones
        for association in associations:
            hazardtype, hazardlevel = association.split(' - ')
            if not obj.has_association(hazardtype, hazardlevel):
                hazardcategory = HazardCategory.get(hazardtype, hazardlevel)
                order = DBSession.query(
                        func.coalesce(
                            func.cast(
                                func.max(HcTr.order),
                                Integer),
                            0)) \
                    .select_from(HcTr) \
                    .filter(HcTr.hazardcategory_id == hazardcategory.id) \
                    .first()[0] + 1

                record = HcTr(
                    hazardcategory=hazardcategory,
                    order=order)
                obj.hazardcategory_associations.append(record)

        DBSession.flush()
        return HTTPFound(request.route_url('admin_technical_rec'))


@view_config(route_name='admin_hazardsets',
             renderer='templates/admin/hazardsets.jinja2')
def hazardsets(request):
    return {
        'hazardsets': DBSession.query(HazardSet)
    }


@view_config(route_name='admin_hazardset',
             renderer='templates/admin/hazardset.jinja2')
def hazardset(request):
    id = request.matchdict['hazardset']
    hazardset = DBSession.query(HazardSet) \
        .options(joinedload(HazardSet.layers).joinedload(Layer.hazardlevel)) \
        .get(id)
    return {
        'hazardset': hazardset
    }


@view_config(route_name='admin_admindiv_hazardsets')
def admindiv_hazardsets(request):
    hazardtype = DBSession.query(HazardType).first()
    return HTTPFound(request.route_url('admin_admindiv_hazardsets_hazardtype',
                                       hazardtype=hazardtype.mnemonic))


@view_config(route_name='admin_admindiv_hazardsets_hazardtype',
             renderer='templates/admin/admindiv_hazardsets.jinja2')
def admindiv_hazardsets_hazardtype(request):

    try:
        hazardtype = request.matchdict.get('hazardtype')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"hazardtype"')

    if HazardType.get(hazardtype) is None:
        raise HTTPBadRequest(detail='hazardtype doesn\'t exist')

    query = DBSession.query(AdministrativeDivision) \
        .join(HazardCategoryAdministrativeDivisionAssociation) \
        .join(HazardCategory) \
        .join(HazardType) \
        .filter(HazardType.mnemonic == hazardtype) \
        .join(AdminLevelType) \
        .filter(AdminLevelType.id == 3) \
        .order_by(AdministrativeDivision.name) \
        .options(contains_eager(AdministrativeDivision.hazardcategories))

    data = [{
        'code': row.code,
        'name': row.name,
        'level_2': row.parent.name,
        'level_1': row.parent.parent.name,
        'hazardset': row.hazardcategories[0].hazardsets[0].id
    } for row in query]

    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)
    return {
        'hazard_types': hazard_types,
        'data': json.dumps(data)
    }


@view_config(route_name='admin_climate_rec')
def climate_rec(request):
    hazardtype = DBSession.query(HazardType).first()
    return HTTPFound(request.route_url('admin_climate_rec_hazardtype',
                                       hazard_type=hazardtype.mnemonic))


@view_config(route_name='admin_climate_rec_hazardtype',
             renderer='templates/admin/climate_rec_index.jinja2')
def climate_rec_hazardtype(request):
    hazard_type = request.matchdict['hazard_type']
    hazardtype = HazardType.get(hazard_type)
    if hazardtype is None:
        raise HTTPNotFound

    hazard_types = DBSession.query(HazardType).order_by(HazardType.order)

    climate_recs = DBSession.query(ClimateChangeRecommendation) \
        .filter(ClimateChangeRecommendation.hazardtype == hazardtype)
    return {
        'hazard_types': hazard_types,
        'climate_recs': climate_recs
        }


@view_config(route_name='admin_climate_rec_new',
             renderer='templates/admin/climate_rec_form.jinja2')
def climate_rec_new(request):
    hazard_type = request.matchdict['hazard_type']
    hazardtype = HazardType.get(hazard_type)
    if hazardtype is None:
        raise HTTPNotFound

    obj = ClimateChangeRecommendation()
    obj.hazardtype = hazardtype
    return climate_rec_process(request, obj)


@view_config(route_name='admin_climate_rec_edit',
             renderer='templates/admin/climate_rec_form.jinja2')
def climate_rec_edit(request):
    id = request.matchdict['id']
    obj = DBSession.query(ClimateChangeRecommendation).get(id)
    if obj is None:
        raise HTTPNotFound()
    return climate_rec_process(request, obj)


def climate_rec_process(request, obj):
    if request.method == 'GET':
        hazard_types = DBSession.query(HazardType).order_by(HazardType.order)

        association_subq = DBSession.query(CcrAd) \
            .filter(CcrAd.hazardtype == obj.hazardtype) \
            .subquery()

        admin_divs = DBSession.query(
                AdministrativeDivision,
                ClimateChangeRecommendation) \
            .select_from(AdministrativeDivision) \
            .outerjoin(association_subq,
                       association_subq.c.administrativedivision_id ==
                       AdministrativeDivision.id) \
            .outerjoin(ClimateChangeRecommendation,
                       ClimateChangeRecommendation.id ==
                       association_subq.c.climatechangerecommendation_id) \
            .join(AdminLevelType) \
            .filter(AdminLevelType.mnemonic == u'COU') \
            .order_by(AdministrativeDivision.name)

        if obj.id is None:
            action = request.route_url('admin_climate_rec_new',
                                       hazard_type=obj.hazardtype.mnemonic)
        else:
            action = request.route_url('admin_climate_rec_edit', id=obj.id)
        return {
            'obj': obj,
            'action': action,
            'hazard_types': hazard_types,
            'admin_divs': admin_divs
        }

    if request.method == 'POST':
        if inspect(obj).transient:
            DBSession.add(obj)

        obj.hazardtype = HazardType.get(request.POST.get('hazard_type'))
        obj.text = request.POST.get('text')

        admindiv_ids = request.POST.getall('associations')

        # Remove unchecked ones
        for association in obj.associations:
            if association.administrativedivision_id not in admindiv_ids:
                DBSession.delete(association)

        # Add new ones
        for admindiv_id in admindiv_ids:
            association = DBSession.query(CcrAd) \
                .get((admindiv_id, obj.hazardtype.id))
            if association is None:
                association = CcrAd(
                    administrativedivision_id=admindiv_id,
                    hazardtype=obj.hazardtype)
                obj.associations.append(association)
            else:
                association.climatechangerecommendation = obj

        DBSession.flush()
        return HTTPFound(request.route_url('admin_climate_rec_edit',
                         id=obj.hazardtype.mnemonic))
