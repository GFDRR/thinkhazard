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

import os
import re
import logging
import traceback
import httplib2
from urllib.parse import urlencode
from urllib.parse import urlunsplit
import json
import csv
from datetime import datetime
import pytz
from time import sleep

from thinkhazard.models import (
    HazardLevel,
    HazardSet,
    HazardType,
    Layer,
    Output,
    Region,
    AdministrativeDivision,
    FurtherResource,
    HazardTypeFurtherResourceAssociation,
    Harvesting,
)
from thinkhazard.processing import BaseProcessor


logger = logging.getLogger(__name__)

region_admindiv_csv_path = "data/geonode_regions_to_administrative_divisions_code.csv"

# FIXME: temporary override
excluded_hazardsets = [
    'LS(EQ)-GLOBAL-ARUP',
    'LS(PP)-GLOBAL-ARUP',
]

cache_path = '/tmp/geonode_api'


def warning(object, msg):
    logger.warning(("{csw_type} {id}: " + msg).format(**object))


def parse_date(str):
    if str is None or len(str) == 0:
        return None
    if "." in str:
        return datetime.strptime(str, "%Y-%m-%dT%H:%M:%S.%f")
    else:
        return datetime.strptime(str, "%Y-%m-%dT%H:%M:%S")


def between(value, range):
    """Test hazard_period against value or interval in settings"""
    if not isinstance(range, list):
        range = [range, range]
    if range[0] <= value <= range[1]:
        return True
    return False


class Harvester(BaseProcessor):

    # We load system ca bundle in order to trust let's encrypt certificates
    http_client = httplib2.Http(ca_certs="/etc/ssl/certs/ca-certificates.crt")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_cache = False

    @staticmethod
    def argument_parser():
        parser = BaseProcessor.argument_parser()
        parser.add_argument(
            "--hazard-type",
            dest="hazard_type",
            action="store",
            help="The hazard type (ie. earthquake, ...)",
        )
        parser.add_argument(
            "--use-cache",
            dest="use_cache",
            action="store_const",
            const=True,
            default=False,
            help="Use geonode local cache (for development)",
        )
        return parser

    def do_execute(self, hazard_type=None, use_cache=False):
        self.use_cache = use_cache

        setting_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "thinkhazard_processing.yaml"
        )
        settings_mtime = datetime.utcfromtimestamp(
            os.path.getmtime(setting_path)
        ).replace(tzinfo=pytz.utc)

        last_complete_harvesting_date = Harvesting.last_complete_date(self.dbsession)
        if (
            last_complete_harvesting_date is None
            or settings_mtime > last_complete_harvesting_date
        ):
            logger.info(
                "Settings have been modified, " "passing in force/complete mode."
            )
            self.force = True
            self.hazard_type = None

        try:
            self.harvest_regions()
            self.create_region_admindiv_associations()
        except Exception:
            logger.error(traceback.format_exc())
            logger.info("Continue with layers")

        try:
            self.harvest_layers(hazard_type)
        except Exception:
            logger.error(traceback.format_exc())
            logger.info("Continue with documents")

        try:
            self.harvest_documents()
        except Exception:
            logger.error(traceback.format_exc())

        Harvesting.new(self.dbsession, complete=(self.force is True and hazard_type is None))

    def request(self, url):
        """
        Send request and retry in case of 503 (unavailable).
        """

        tmp_path = os.path.join(cache_path, url.replace("/", '_').replace(":", '_'))
        if self.use_cache and os.path.isfile(tmp_path):

            class DummyResponse():
                pass

            with open(tmp_path) as f:
                content = f.read()
                response = DummyResponse()
                response.status = 200

        else:
            tries = 3
            while tries > 0:
                response, content = self.http_client.request(url)
                if response.status != 503:
                    break
                sleep(3)
                tries -= 1

            if self.use_cache and response.status == 200:
                with open(tmp_path, "wb") as f:
                    f.write(content)

        return response, content

    def fetch(self, category, params={}, order_by="title"):
        geonode = self.settings["geonode"]
        # add credentials
        params["username"] = geonode["username"]
        params["api_key"] = geonode["api_key"]
        # get all entries (geonode default limit is 200)
        params["limit"] = 0
        url = urlunsplit(
            (
                geonode["scheme"],
                geonode["netloc"],
                "api/{}/".format(category),
                urlencode(params),
                "",
            )
        )
        logger.info("Retrieving {}".format(url))
        response, content = self.request(url)
        if response.status != 200:
            raise Exception(u'Geonode returned status {}: {}'.
                            format(response.status, content))
        o = json.loads(content)
        return sorted(o["objects"], key=lambda object: object[order_by])

    def hazardtype_from_geonode(self, geonode_name):
        for mnemonic, type_settings in self.settings["hazard_types"].items():
            if type_settings["hazard_type"] == geonode_name:
                return HazardType.get(self.dbsession, str(mnemonic))
        return None

    def check_hazard_type(self, object):
        hazard_type = object["hazard_type"]
        if not hazard_type:
            warning(object, "hazard_type is empty")
            return False
        hazardtype = self.hazardtype_from_geonode(hazard_type)
        if hazardtype is None:
            warning(object, "hazard_type not supported: {hazard_type}")
        return hazardtype

    def create_region_admindiv_associations(self):
        with open(region_admindiv_csv_path, "r") as csvfile:
            rows = csv.reader(csvfile, delimiter=",")
            for row in rows:
                try:
                    with self.dbsession.begin_nested():
                        self.create_region_admindiv_association(row)
                except Exception:
                    logger.error(
                        "Linking region {} & admin div {} failed".format(row[1], row[2])
                    )
                    logger.error(traceback.format_exc())

    def create_region_admindiv_association(self, row):
        # row[0] is geonode region's name_en (useless here)
        # row[1] is geonode region id
        # row[2] is GAUL administrative division **code** (not id!)
        region = self.dbsession.query(Region).filter(Region.id == row[1]).one_or_none()

        if region is None:
            logger.warning(
                "Region {} id {} does not exist in GeoNode".format(row[0], row[1])
            )
            return False

        admindiv = (
            self.dbsession.query(AdministrativeDivision)
            .filter(AdministrativeDivision.code == row[2])
            .one_or_none()
        )

        if admindiv is None:
            logger.warning(
                "AdminUnit code {} is not in our GAUL dataset".format(row[2])
            )
            return False

        region.administrativedivisions.append(admindiv)
        self.dbsession.flush()

    def harvest_regions(self):
        regions = self.fetch("regions", order_by="name")
        for region in regions:
            try:
                with self.dbsession.begin_nested():
                    self.harvest_region(region)
            except Exception as e:
                logger.error(
                    "Region {} raises an exception :\n{}".format(
                        region["name"], str(e)
                    )
                )
                logger.error(traceback.format_exc())

    def harvest_region(self, object):
        logger.info("Harvesting region {id} - {name_en}".format(**object))
        name = object["name_en"]
        id = object["id"]

        region = self.dbsession.query(Region).filter(Region.id == id).one_or_none()

        if region is None:
            region = Region()
            region.id = id
            logger.info("  Creating new Region - {}".format(name))
        else:
            logger.info("  Updating Region - {}".format(name))
            # drop existing relationships with GAUL administrative divisions
            for ad in region.administrativedivisions:
                region.administrativedivisions.remove(ad)

        region.name = name
        region.level = object["level"]
        self.dbsession.add(region)
        self.dbsession.flush()

    def harvest_documents(self):
        documents = self.fetch("documents")
        for doc in documents:
            try:
                with self.dbsession.begin_nested():
                    self.harvest_document(doc)
            except Exception as e:
                logger.error(
                    "Document {} raises an exception :\n{}".format(
                        doc["title"], str(e)
                    )
                )
                logger.error(traceback.format_exc())

    def harvest_document(self, object):
        logger.info("Harvesting document {id} - {title}".format(**object))
        title = object["title"]
        id = object["id"]

        # we need to retrieve more information on this document
        # since the regions array is not advertised by the main
        # regions listing from GeoNode
        geonode = self.settings["geonode"]
        doc_url = urlunsplit(
            (
                geonode["scheme"],
                geonode["netloc"],
                "api/documents/{}/".format(id),
                urlencode(
                    {"username": geonode["username"], "api_key": geonode["api_key"]}
                ),
                "",
            )
        )
        logger.info("  Retrieving {}".format(doc_url))
        response, content = self.request(doc_url)
        if response.status != 200:
            raise Exception(u'Geonode returned status {}: {}'.
                            format(response.status, content))

        o = json.loads(content)

        if 'regions' not in list(o.keys()):
            warning(o, 'Attribute "regions" is missing')

        region_ids = []
        for r in o.get("regions", []):
            # r is like "/api/regions/1/"
            region_ids.append(r.split("/")[3])

        if len(region_ids) == 0:
            regions = []
        else:
            regions = self.dbsession.query(Region).filter(Region.id.in_(region_ids)).all()

        hazardtypes = self.collect_hazard_types(o)
        if not hazardtypes:
            return False

        furtherresource = (
            self.dbsession.query(FurtherResource)
            .filter(FurtherResource.id == id)
            .one_or_none()
        )

        if furtherresource is None:
            furtherresource = FurtherResource()
            furtherresource.id = id
            logger.info("  Creating new FurtherResource")
        else:
            logger.info("  Updating FurtherResource")
            # drop existing relationships
            assocs = (
                self.dbsession.query(HazardTypeFurtherResourceAssociation)
                .filter(HazardTypeFurtherResourceAssociation.furtherresource_id == id)
                .all()
            )
            for a in assocs:
                self.dbsession.delete(a)

        furtherresource.text = title
        for region in regions:
            for type in hazardtypes:
                association = HazardTypeFurtherResourceAssociation()
                association.hazardtype = type
                association.region = region
                logger.info(
                    "  Linked with Region {} for HazardType {}".format(
                        region.name, type.mnemonic
                    )
                )
                furtherresource.hazardtype_associations.append(association)

        self.dbsession.add(furtherresource)
        self.dbsession.flush()

    def collect_hazard_types(self, object):
        # handle documents linked to several hazard types
        # eg, those with:
        #   hazard_type: "river_flood",
        #   supplemental_information: "drought, climate_change",
        primary_type = self.check_hazard_type(object)
        if not primary_type:
            return False
        if object["csw_type"] == "document":
            # supplemental information holds additional hazard types
            hazard_types = [primary_type]
            more = object["supplemental_information"]
            if more == "No information provided":
                logger.info("  Supplemental_information is empty")
            else:
                # we assume the form:
                # "drought, river_flood, tsunami, coastal_flood, strong_wind"
                logger.info("  Supplemental_information is {}".format(more))
                types = re.split(r"\s*,\s*", more)
                for type in types:
                    if type != "":
                        tmp_object = {
                            "csw_type": object["csw_type"],
                            "id": object["id"],
                            "title": object["title"],
                            "hazard_type": type,
                        }
                        hazardtype = self.check_hazard_type(tmp_object)
                        if hazardtype:
                            hazard_types.append(hazardtype)
            return hazard_types
        else:
            return [primary_type]

    def harvest_layers(self, hazard_type=None):
        if self.force:
            logger.info("Cleaning previous data")
            self.dbsession.query(Output).delete()
            self.dbsession.query(Layer).delete()
            self.dbsession.query(HazardSet).delete()
            self.dbsession.flush()

        layers_db = self.dbsession.query(Layer).all()
        for layer in layers_db:
            layer.set_harvested(False)

        # see https://docs.djangoproject.com/en/1.8/ref/models/querysets
        params = {}
        if hazard_type is not None:
            params["hazard_type__in"] = hazard_type
        else:
            params["hazard_type__isnull"] = "False"

        layers = self.fetch("layers", params)
        for layer in layers:
            try:
                with self.dbsession.begin_nested():
                    self.harvest_layer(layer)
            except Exception as e:
                logger.error(
                    "Layer {} raises an exception :\n{}".format(
                        layer["title"], str(e)
                    )
                )
                logger.error(traceback.format_exc())

        for layer in layers_db:
            if not layer.is_harvested():
                self.delete_layer(layer)

        self.select_levels()

        self.dbsession.flush()

    def delete_layer(self, layer):
        logger.info("Deleting layer {}-{}".format(layer.hazardset_id, layer.return_period))

        hazardset = layer.hazardset

        layer.hazardset.layers.remove(layer)
        self.dbsession.delete(layer)

        if len(hazardset.layers) == 0:
            logger.info("Deleting hazardset {}".format(hazardset.id))
            self.dbsession.query(Output).filter(Output.hazardset_id == hazardset.id).delete()
            self.dbsession.delete(hazardset)
        else:
            logger.info("Keeping hazardset {}".format(hazardset.id))
            hazardset.completed = False
            hazardset.processed = None

    def select_levels(self):
        for hazardset in self.dbsession.query(HazardSet):
            type_settings = self.settings["hazard_types"][hazardset.hazardtype.mnemonic]
            preprocessed = "values" in type_settings
            if preprocessed:
                continue

            for level_mne in ('HIG', 'MED', 'LOW'):
                level = HazardLevel.get(self.dbsession, level_mne)
                self.select_layer_for_level(hazardset, level)

            if type_settings.get("mask_return_period"):
                self.select_mask_layer(hazardset)

            # Purge superseeded layers
            self.dbsession.query(Layer) \
                .filter(Layer.hazardset_id == hazardset.id) \
                .filter(Layer.hazardlevel_id.is_(None)) \
                .filter(Layer.mask.is_(False)) \
                .delete()

    def select_layer_for_level(self, hazardset, level):
        type_settings = self.settings["hazard_types"][hazardset.hazardtype.mnemonic]
        layer = self.select_layer_for_range(hazardset, type_settings["return_periods"][level.mnemonic])
        if layer is None:
            return
        if layer.hazardlevel != level:
            looser = hazardset.layer_by_level(level.mnemonic)
            if looser is not None:
                looser.hazardlevel = None
            layer.hazardlevel = level
            hazardset.complete = False
            hazardset.processed = None

    def select_mask_layer(self, hazardset):
        type_settings = self.settings["hazard_types"][hazardset.hazardtype.mnemonic]
        layer = self.select_layer_for_range(hazardset, type_settings["mask_return_period"])
        if layer is None:
            return
        if not layer.mask:
            looser = hazardset.mask_layer()
            if looser is not None:
                looser.mask = False
            layer.mask = True
            hazardset.complete = False
            hazardset.processed = None

    def select_layer_for_range(self, hazardset, range):
        winner = None
        for layer in hazardset.layers:
            if between(layer.return_period, range):
                if winner is None:
                    winner = layer
                else:
                    if layer.return_period < winner.return_period:
                        winner = layer
        return winner

    def harvest_layer(self, object):
        logger.info("Harvesting layer {id} - {title}".format(**object))
        title = object["title"]

        # we need to retrieve more information on this layer
        # since the regions array is not advertised by the main
        # regions listing from GeoNode
        geonode = self.settings["geonode"]
        layer_url = urlunsplit(
            (
                geonode["scheme"],
                geonode["netloc"],
                "api/layers/{id}/".format(**object),
                urlencode(
                    {"username": geonode["username"], "api_key": geonode["api_key"]}
                ),
                "",
            )
        )
        logger.info("  Retrieving {}".format(layer_url))
        response, content = self.request(layer_url)
        if response.status != 200:
            raise Exception(u'Geonode returned status {}: {}'.
                            format(response.status, content))

        o = json.loads(content)

        if "regions" not in list(o.keys()):
            warning(object, 'Attribute "regions" is missing')

        region_ids = []
        for r in o.get("regions", []):
            # r is like "/api/regions/1/"
            region_ids.append(r.split("/")[3])

        if len(region_ids) == 0:
            regions = []
        else:
            regions = self.dbsession.query(Region).filter(Region.id.in_(region_ids)).all()

        hazardset_id = o['hazard_set']
        if not hazardset_id:
            logger.info("  hazard_set is empty")
            return False

        # FIXME: temporary override
        if hazardset_id in excluded_hazardsets:
            logger.info("  hazard_set {} is excluded, skipping")
            return False

        hazardtype = self.check_hazard_type(o)
        if not hazardtype:
            return False

        type_settings = self.settings["hazard_types"][hazardtype.mnemonic]
        preprocessed = "values" in type_settings

        local = "GLOBAL" not in hazardset_id

        mask = False
        if preprocessed is True:
            hazardlevel = None
            hazard_unit = None
            if o['hazard_period']:
                logger.info('  return period found in preprocessed hazardset')
                return False
            hazard_period = None

        else:
            hazard_period = int(o['hazard_period'])
            hazardlevel = None
            for level in ("LOW", "MED", "HIG"):
                if between(hazard_period, type_settings["return_periods"][level]):
                    hazardlevel = HazardLevel.get(self.dbsession, level)
                    break

            if "mask_return_period" in type_settings and between(
                hazard_period, type_settings["mask_return_period"]
            ):
                mask = True

            if hazardlevel is None and not mask:
                logger.info("  No corresponding hazard_level")
                return False

            hazard_unit = o['hazard_unit']
            if hazard_unit == '':
                logger.info('  hazard_unit is empty')
                return False

        if o['srid'] != 'EPSG:4326':
            logger.info('  srid is different from "EPSG:4326"')
            return False

        data_update_date = parse_date(o['data_update_date'])
        if not data_update_date:
            warning(o, 'data_update_date is empty')
            # We use a very old date for good comparison in decision tree
            data_update_date = datetime.fromtimestamp(0)

        metadata_update_date = parse_date(o['metadata_update_date'])
        if not metadata_update_date:
            warning(o, 'metadata_update_date is empty')
            # We use a very old date for good comparison in decision tree
            metadata_update_date = datetime.fromtimestamp(0)

        calculation_method_quality = o['calculation_method_quality']
        if not calculation_method_quality:
            warning(o, 'calculation_method_quality is empty')
            return False
        calculation_method_quality = int(float(calculation_method_quality))

        scientific_quality = o['scientific_quality']
        if not scientific_quality:
            warning(o, 'scientific_quality is empty')
            return False
        scientific_quality = int(float(scientific_quality))

        download_url = o['download_url']
        if not download_url:
            warning(o, 'download_url is empty')
            return False

        hazardset = self.dbsession.query(HazardSet).get(hazardset_id)

        # Create hazardset before layer
        if hazardset is None:
            logger.info("  Create new hazardset {}".format(hazardset_id))
            hazardset = HazardSet()
            hazardset.id = hazardset_id
            hazardset.hazardtype = hazardtype
            self.dbsession.add(hazardset)

        # get detail_url and owner_organization from last updated layer
        geonode = self.settings["geonode"]
        geonode_base_url = "%s://%s" % (geonode["scheme"], geonode["netloc"])

        if o['detail_url'] and not mask:
            hazardset.detail_url = geonode_base_url + o['detail_url']
        if o['owner']['organization'] and not mask:
            hazardset.owner_organization = o['owner']['organization']
        if not mask:
            hazardset.regions = regions

        layer = self.dbsession.query(Layer).get(o['id'])
        if layer is None:
            logger.info("  Create new Layer {}".format(title))
            layer = Layer()
            layer.geonode_id = o['id']
            layer.hazardset = hazardset
            layer.mask = False

        else:
            # If data has changed
            if (
                layer.data_lastupdated_date != data_update_date
                or layer.download_url != download_url
            ):
                logger.info("  Invalidate downloaded")
                layer.downloaded = False
                hazardset.complete = False
                hazardset.processed = None
                # Remove file from cache
                layer.download_url = download_url
                os.unlink(self.layer_path(layer))

            # Some hazardset fields are calculated during completing
            if (
                layer.calculation_method_quality != calculation_method_quality
                or layer.scientific_quality != scientific_quality
                or layer.metadata_lastupdated_date != metadata_update_date
            ):
                logger.info("  Invalidate complete")
                hazardset.complete = False

            # Some fields invalidate outputs
            if layer.hazardunit != hazard_unit:
                logger.info("  Invalidate processed")
                hazardset.processed = None

        typename = o.get("typename", None)
        if typename is None:
            warning(o, 'Attribute "typename" is missing')
        layer.typename = typename

        layer.return_period = hazard_period
        layer.hazardunit = hazard_unit
        layer.data_lastupdated_date = data_update_date
        layer.metadata_lastupdated_date = metadata_update_date
        layer.download_url = download_url

        # TODO: retrieve quality attributes
        layer.calculation_method_quality = calculation_method_quality
        layer.scientific_quality = scientific_quality
        layer.local = local

        layer.set_harvested(True)
        self.dbsession.flush()
        return True
