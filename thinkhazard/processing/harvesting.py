# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 by the GFDRR / World Bank
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

import logging
import httplib2
from urllib import urlencode
from urlparse import urlunsplit
import json
import transaction
from datetime import datetime

from ..models import (
    DBSession,
    HazardLevel,
    HazardSet,
    HazardType,
    Layer,
    Output,
    FurtherResource,
    HazardTypeFurtherResourceAssociation,
    )

from . import settings


logger = logging.getLogger(__name__)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.setLevel(logging.DEBUG)


geonode = settings['geonode']


def clearall():
    logger.info(u'Cleaning previous data')
    DBSession.query(Output).delete()
    DBSession.query(Layer).delete()
    DBSession.query(HazardSet).delete()
    DBSession.flush()


def fetch(url):
    logger.info(u'Retrieving {}'.format(url))
    h = httplib2.Http()
    response, content = h.request(url)
    o = json.loads(content)
    return sorted(o['objects'], key=lambda object: object['title'])


def harvest(hazard_type=None, force=False, dry_run=False):
    if force:
        try:
            clearall()
            if dry_run:
                transaction.abort()
            else:
                transaction.commit()
        except:
            transaction.abort()
            raise

    params = {}
    if hazard_type is not None:
        params['hazard_type__in'] = hazard_type

    layers_url = urlunsplit((geonode['scheme'],
                             geonode['netloc'],
                             'api/layers/',
                             urlencode(params),
                             ''))

    layers = fetch(layers_url)
    documents = fetch(layers_url.replace('layers', 'documents'))

    for layer in layers:
        if harvest_layer(layer):
            try:
                if dry_run:
                    transaction.abort()
                else:
                    transaction.commit()
            except Exception as e:
                transaction.abort()
                logger.error(u'{} raise an exception :\n{}'
                             .format(layer['title'], e.message))

    for doc in documents:
        harvest_document(doc)
        try:
            if dry_run:
                transaction.abort()
            else:
                transaction.commit()
        except Exception as e:
            transaction.abort()
            logger.error(u'{} raise an exception :\n{}'
                         .format(doc['title'], e.message))


def check_hazard_type(object):
    title = object['title']
    hazard_type = object['hazard_type']

    if not hazard_type:
        logger.warning(u'{} - hazard_type is empty'.format(title))
        return False
    hazardtype = hazardtype_from_geonode(hazard_type)
    if hazardtype is None:
        logger.warning(u'{} - hazard_type not supported: {}'
                       .format(title, hazard_type))
    return hazardtype


def collect_hazard_types(object):
    # handle documents linked to several hazard types
    # eg, those with:
    #   hazard_type: "river_flood",
    #   supplemental_information: "drought, climate_change",
    primary_type = check_hazard_type(object)
    if not primary_type:
        return False
    if object['csw_type'] == "document":
        # supplemental information holds additional hazard types
        hazard_types = [primary_type]
        more = object['supplemental_information']
        if more == u'No information provided':
            logger.info(u'{} - supplemental_information is empty'
                        .format(object['title']))
        else:
            # we assume the form:
            # "drought, river_flood, tsunami, coastal_flood, strong_wind"
            logger.info(u'{} - supplemental_information is {}'
                        .format(object['title'], more))
            types = more.split(', ')
            for type in types:
                object['hazard_type'] = type
                hazardtype = check_hazard_type(object)
                if hazardtype:
                    hazard_types.append(hazardtype)
        return hazard_types
    else:
        return [primary_type]


def harvest_document(object):
    title = object['title']
    id = object['id']

    hazardtypes = collect_hazard_types(object)
    if not hazardtypes:
        return False

    furtherresource = DBSession.query(FurtherResource) \
        .filter(FurtherResource.id == id) \
        .one_or_none()

    if furtherresource is None:
        furtherresource = FurtherResource()
        furtherresource.id = id
        logger.info(u'Creating new FurtherResource - {}'.format(title))
    else:
        logger.info(u'Updating FurtherResource - {}'.format(title))
        # drop existing relationships
        assocs = DBSession.query(HazardTypeFurtherResourceAssociation) \
            .filter(HazardTypeFurtherResourceAssociation
                    .furtherresource_id == id).all()
        for a in assocs:
            DBSession.delete(a)

    furtherresource.text = title
    for type in hazardtypes:
        # TODO: handle relationship order (?):
        association = HazardTypeFurtherResourceAssociation(order=1)
        association.hazardtype = type
        furtherresource.hazardtype_associations.append(association)

    DBSession.add(furtherresource)
    DBSession.flush()


def harvest_layer(object):
    title = object['title']

    hazardset_id = object['hazard_set']
    if not hazardset_id:
        logger.info(u'{} - hazard_set is empty'.format(title))
        return False

    hazardtype = check_hazard_type(object)
    if not hazardtype:
        return False

    type_settings = settings['hazard_types'][hazardtype.mnemonic]
    preprocessed = 'values' in type_settings

    local = 'GLOBAL' not in hazardset_id

    mask = False
    if preprocessed is True:
        hazardlevel = None
        hazard_unit = None
        if object['hazard_period']:
            logger.info(u'{} - Has a return period'.format(title))
            return False
        hazard_period = None
    else:
        hazard_period = int(object['hazard_period'])
        hazardlevel = None
        for level in (u'LOW', u'MED', u'HIG'):
            return_periods = type_settings['return_periods'][level]
            if isinstance(return_periods, list):
                if (hazard_period >= return_periods[0] and
                        hazard_period <= return_periods[1]):
                    hazardlevel = HazardLevel.get(level)
                    break
            else:
                if hazard_period == return_periods:
                    hazardlevel = HazardLevel.get(level)

        if ('mask_return_period' in type_settings and
                hazard_period == type_settings['mask_return_period']):
            mask = True

        if hazardlevel is None and not mask:
            logger.info(u'{} - No corresponding hazard_level'.format(title))
            return False

        hazard_unit = object['hazard_unit']
        if hazard_unit == '':
            logger.info(u'{} -  hazard_unit is empty'.format(title))
            return False

    if object['srid'] != 'EPSG:4326':
        logger.info(u'{} - srid is different from "EPSG:4326"'
                    .format(title))
        return False

    data_update_date = object['data_update_date']
    if not data_update_date:
        logger.warning(u'{} - data_update_date is empty'.format(title))
        # TODO: Restore bypassed constraint to get Volcanic data
        # return False
        data_update_date = datetime.now()

    metadata_update_date = object['metadata_update_date']
    if not metadata_update_date:
        logger.warning(u'{} - metadata_update_date is empty'.format(title))
        # return False
        metadata_update_date = datetime.now()

    calculation_method_quality = object['calculation_method_quality']
    if not calculation_method_quality:
        logger.warning(u'{} - calculation_method_quality is empty'
                       .format(title))
        return False
    calculation_method_quality = int(float(calculation_method_quality))

    scientific_quality = object['scientific_quality']
    if not scientific_quality:
        logger.warning(u'{} - scientific_quality is empty'.format(title))
        return False
    scientific_quality = int(float(scientific_quality))

    download_url = object['download_url']
    if not download_url:
        logger.warning(u'{} - download_url is empty'.format(title))
        return False

    hazardset = DBSession.query(HazardSet).get(hazardset_id)
    if hazardset is None:

        logger.info(u'{} - Create new hazardset {}'
                    .format(title, hazardset_id))
        hazardset = HazardSet()
        hazardset.id = hazardset_id
        hazardset.hazardtype = hazardtype
        hazardset.data_lastupdated_date = data_update_date
        hazardset.metadata_lastupdated_date = metadata_update_date
        # get distribution_url and owner_organization from 1st layer of dataset
        hazardset.distribution_url = object['distribution_url']
        hazardset.owner_organization = object['owner__organization']
        DBSession.add(hazardset)
    else:
        # print '  Hazardset {} found'.format(hazardset_id)
        pass

    layer = DBSession.query(Layer) \
        .filter(Layer.hazardset_id == hazardset_id)
    if hazardlevel is not None:
        layer = layer.filter(Layer.hazardlevel_id == hazardlevel.id)
    if mask:
        layer = layer.filter(Layer.mask.is_(True))
    layer = layer.first()

    if layer is None:
        layer = Layer()
        logger.info(u'Creating new Layer - {}'.format(title))
        DBSession.add(layer)

    else:
        if object['id'] == layer.geonode_id:
            # TODO: metadata change
            return False

        if hazard_period > layer.return_period:
            logger.info(u'{} - Use preferred return period {}'
                        .format(title, layer.return_period))
            return False

        logger.info(u'{} - Replace layer for level {}'
                    .format(title, hazardlevel.mnemonic))

    layer.hazardset = hazardset
    layer.hazardlevel = hazardlevel
    layer.mask = mask
    layer.return_period = hazard_period
    layer.hazardunit = hazard_unit
    layer.data_lastupdated_date = data_update_date
    layer.metadata_lastupdated_date = metadata_update_date
    layer.geonode_id = object['id']
    layer.download_url = download_url

    # TODO: retrieve quality attributes
    layer.calculation_method_quality = calculation_method_quality
    layer.scientific_quality = scientific_quality
    layer.local = local
    DBSession.flush()
    return True


def hazardtype_from_geonode(geonode_name):
    for mnemonic, type_settings in settings['hazard_types'].iteritems():
        if type_settings['hazard_type'] == geonode_name:
            return HazardType.get(unicode(mnemonic))
    return None
