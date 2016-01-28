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
    logger.info('Cleaning previous data')
    DBSession.query(Output).delete()
    DBSession.query(Layer).delete()
    DBSession.query(HazardSet).delete()
    DBSession.flush()


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

    hazard_type_url = urlunsplit((geonode['scheme'],
                                  geonode['netloc'],
                                  'api/layers/',
                                  urlencode(params),
                                  ''))

    logger.info('Retrieving {}'.format(hazard_type_url))
    h = httplib2.Http()
    response, content = h.request(hazard_type_url)
    metadata = json.loads(content)

    objects = sorted(metadata['objects'], key=lambda object: object['title'])

    for object in objects:
        if harvest_layer(object):
            try:
                if dry_run:
                    transaction.abort()
                else:
                    transaction.commit()
            except Exception as e:
                transaction.abort()
                logger.error('{} raise an exception :\n{}'
                             .format(object['title'], e.message))


def harvest_layer(object, dry_run=False):
    title = object['title']

    hazardset_id = object['hazard_set']
    if not hazardset_id:
        logger.info('{} - hazard_set is empty'.format(title))
        return False

    hazard_type = object['hazard_type']
    if not hazard_type:
        logger.warning('{} - hazard_type is empty'.format(title))
        return False
    hazardtype = hazardtype_from_geonode(hazard_type)
    if hazardtype is None:
        logger.warning('{} - hazard_type not supported: {}'
                       .format(title, hazard_type))
        return False

    type_settings = settings['hazard_types'][hazardtype.mnemonic]
    preprocessed = 'values' in type_settings

    local = 'GLOBAL' not in hazardset_id

    mask = False
    if preprocessed is True:
        hazardlevel = None
        hazard_unit = None
        if object['hazard_period']:
            logger.info('{} - Has a return period'.format(title))
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
            logger.info('{} - No corresponding hazard_level'.format(title))
            return False

        hazard_unit = object['hazard_unit']
        if hazard_unit == '':
            logger.info('{} -  hazard_unit is empty'.format(title))
            return False

    if object['srid'] != 'EPSG:4326':
        logger.info('{} - srid is different from "EPSG:4326"'
                    .format(title))
        return False

    data_update_date = object['data_update_date']
    if not data_update_date:
        logger.warning('{} - data_update_date is empty'.format(title))
        # TODO: Restore bypassed constraint to get Volcanic data
        # return False
        data_update_date = datetime.now()

    metadata_update_date = object['metadata_update_date']
    if not metadata_update_date:
        logger.warning('{} - metadata_update_date is empty'.format(title))
        # return False
        metadata_update_date = datetime.now()

    calculation_method_quality = object['calculation_method_quality']
    if not calculation_method_quality:
        logger.warning('{} - calculation_method_quality is empty'
                       .format(title))
        return False
    calculation_method_quality = int(float(calculation_method_quality))

    scientific_quality = object['scientific_quality']
    if not scientific_quality:
        logger.warning('{} - scientific_quality is empty'.format(title))
        return False
    scientific_quality = int(float(scientific_quality))

    download_url = object['download_url']
    if not download_url:
        logger.warning('{} - download_url is empty'.format(title))
        return False

    hazardset = DBSession.query(HazardSet).get(hazardset_id)
    if hazardset is None:

        logger.info('{} - Create new hazardset {}'
                    .format(title, hazardset_id))
        hazardset = HazardSet()
        hazardset.id = hazardset_id
        hazardset.hazardtype = hazardtype
        hazardset.data_lastupdated_date = data_update_date
        hazardset.metadata_lastupdated_date = metadata_update_date
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
        logger.info('{} - Create new Layer {}'.format(title, title))
        DBSession.add(layer)

    else:
        if object['id'] == layer.geonode_id:
            # TODO: metadata change
            return False

        if hazard_period > layer.return_period:
            logger.info('{} - Use preferred return period {}'
                        .format(title, layer.return_period))
            return False

        logger.info('{} - Replace layer for level {}'
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
