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

import json

from ..models import (
    DBSession,
    AdministrativeDivision,
    AdminLevelType,
    HazardCategory,
    HazardCategoryTechnicalRecommendationAssociation as HcTr,
    HazardCategoryAdministrativeDivisionAssociation,
    HazardLevel,
    HazardType,
    HazardSet,
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
        return HTTPFound(request.route_url('admin_technical_rec_edit',
                                           id=obj.id))


@view_config(route_name='admin_hazardsets',
             renderer='templates/admin/hazardsets.jinja2')
def hazardsets(request):
    return {
        'hazardsets': DBSession.query(HazardSet)
    }


@view_config(route_name='admin_admindiv_hazardsets',
             renderer='templates/admin/admindiv_hazardsets.jinja2')
def admindiv_hazardsets(request):

    try:
        hazardtype = request.matchdict.get('hazardtype')
    except:
        raise HTTPBadRequest(detail='incorrect value for parameter '
                                    '"hazardtype"')

    if HazardType.get(hazardtype) is None:
        raise HTTPBadRequest(detail='hazardtype doesn\'t exist')

    query = DBSession.query(HazardCategoryAdministrativeDivisionAssociation) \
        .join(AdministrativeDivision) \
        .join(HazardCategory) \
        .join(HazardType) \
        .filter(HazardType.mnemonic == hazardtype) \
        .join(AdminLevelType) \
        .filter(AdminLevelType.id == 3) \
        .order_by(AdministrativeDivision.name)

    data = [{
        'code': row.administrativedivision.code,
        'name': row.administrativedivision.name,
        'hazardset': row.hazardsets[0].id
    } for row in query]
    return {
        'data': json.dumps(data)
    }
