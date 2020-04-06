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
import csv
import subprocess
import logging
import requests

from thinkhazard.processing import BaseProcessor
from thinkhazard.models import (
    AdministrativeDivision,
    ClimateChangeRecommendation,
    ClimateChangeRecAdministrativeDivisionAssociation as CcrAd,
    Contact,
    ContactAdministrativeDivisionHazardTypeAssociation as CAdHt,
    HazardType,
    HazardLevel,
    HazardCategory,
    HazardCategoryTechnicalRecommendationAssociation,
    TechnicalRecommendation,
)

LOG = logging.getLogger(__name__)


def table_exists(connection, schema, table):
    sql = """
SELECT count(*) AS count
FROM information_schema.tables
WHERE table_schema = '{schema}'
AND table_name = '{table}';
""".format(schema=schema, table=table)
    result = connection.execute(sql)
    row = result.first()
    return row[0] == 1


class AdministrativeDivisionsImporter(BaseProcessor):
    """
    This script makes it so the database is populated with administrative
    divisions.
    """
    TMP_PATH = "/tmp/admindivs"

    def do_execute(self):
        connection = self.dbsession.connection()
        if self.force:

            # FIXME: we should need this only once per database migration
            connection.execute("""
SELECT SETVAL(
    'datamart.administrativedivision_id_seq',
    COALESCE(MAX(id), 1)
) FROM datamart.administrativedivision;
""")

        for level in (0, 1, 2):

            zip_path = os.path.join(self.TMP_PATH, "adm{}_th.zip".format(level))
            if self.force or not os.path.isfile(zip_path):
                LOG.info("Downloading data for level {}".format(level))
                if os.path.isfile(zip_path):
                    os.unlink(zip_path)
                self.download_zip(level, zip_path)

            shp_path = os.path.join(self.TMP_PATH, "adm{}_th.shp".format(level))
            if self.force or not os.path.isfile(shp_path):
                LOG.info("Decompressing data for level {}".format(level))
                subprocess.run(["unzip", "-o", zip_path, "-d", self.TMP_PATH], check=True)

            if self.force or not table_exists(connection, "public", "adm{}_th".format(level)):
                LOG.info("Importing data for level {}".format(level))
                connection.execute("DROP TABLE adm{level}_th;".format(level))
                self.import_shapefile(shp_path)

            LOG.info("Updating administrative divisions for level {}".format(level))
            connection.execute(self.update_query(0))

            # connection.execute("DROP TABLE adm{level}_th;".format(level))

        # Remove climate change recommendations that are not linked to divisions
        # that don't exist anymore
        connection.execute("""
DELETE from datamart.rel_climatechangerecommendation_administrativedivision
    WHERE administrativedivision_id NOT IN (
          SELECT id
          FROM datamart.administrativedivision
    );""")

        LOG.info(
            "{} administrative divisions created".format(
                self.dbsession.query(AdministrativeDivision).count()
            )
        )

    def import_shapefile(self, path):
        subprocess.run([
            "ogr2ogr",
            "-f", "PostgreSQL",
            "-overwrite",
            "-progress",
            "-nlt", "MULTIPOLYGON",
            "-mapFieldType", "All=String",
            # "-skipfailures",
            # "-limit", "1000",
            "PG:""host=db port=5432 dbname=thinkhazard_admin user=thinkhazard password=thinkhazard""",
            path,
        ], check=True)

    def download_zip(self, level, path):
        if not os.path.isfile(path):
            url = ("https://www.geonode-gfdrrlab.org/geoserver/wfs"
                   "?outputFormat=SHAPE-ZIP"
                   "&service=WFS"
                   "&srs=EPSG%3A4326"
                   "&request=GetFeature"
                   "&format_options=charset%3AUTF-8"
                   "&typename=hazard%3Aadm{}_th"
                   "&version=1.0.0"
                   "&access_token=2ab5cd3e743611ea9ff302a677ac86ab"
                   .format(level))
            try:
                LOG.info('  Retrieving {}'.format(url))
                r = requests.get(url, stream=True)
                r.raise_for_status()

                LOG.info('  Saving to {}'.format(path))
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        f.write(chunk)
            except:
                os.unlink(path)

    def update_query(self, level):
        return """
WITH new_values (
        code,
        leveltype_id,
        name,
        parent_code,
        name_fr,
        name_es,
        geom
    ) AS (
        SELECT
            adm{level}_code::integer,
            {levelplus1},
            adm{level}_name,
            NULL,
            fre,
            esp,
            wkb_geometry
        FROM adm{level}_th
),
upsert AS (
        UPDATE datamart.administrativedivision ad
        SET name = nv.name,
            name_fr = nv.name_fr,
            name_es = nv.name_es,
            geom = nv.geom
        FROM new_values nv
        WHERE ad.code = nv.code
        RETURNING ad.*
    )
INSERT INTO datamart.administrativedivision (
        code,
        leveltype_id,
        name,
        name_fr,
        name_es,
        geom
    )
    SELECT
        code,
        leveltype_id,
        name,
        name_fr,
        name_es,
        geom
    FROM new_values
    WHERE NOT EXISTS (
        SELECT {levelplus1}
        FROM upsert up
        WHERE up.code = new_values.code
);
""".format(level=level, levelplus1=level + 1)


class RecommendationsImporter(BaseProcessor):

    def do_execute(self):
        self.dbsession.query(HazardCategoryTechnicalRecommendationAssociation).delete()
        self.dbsession.query(TechnicalRecommendation).delete()

        # First load general recommendations

        with open("data/general_recommendations.csv", encoding="windows-1252") as csvfile:
            recommendations = csv.reader(csvfile, delimiter=",")
            for row in recommendations:

                hazardcategory = (
                    self.dbsession.query(HazardCategory)
                    .join(HazardLevel)
                    .join(HazardType)
                    .filter(HazardLevel.mnemonic == row[1])
                    .filter(HazardType.mnemonic == row[0])
                    .one()
                )
                hazardcategory.general_recommendation = row[2]
                self.dbsession.add(hazardcategory)

        categories = []
        for type_ in ["EQ", "FL", "CY", "TS", "CF", "VA", "DG"]:
            for level in ["HIG", "MED", "LOW", "VLO"]:
                hazardcategory = (
                    self.dbsession.query(HazardCategory)
                    .join(HazardLevel)
                    .join(HazardType)
                    .filter(HazardLevel.mnemonic == level)
                    .filter(HazardType.mnemonic == type_)
                    .one()
                )
                categories.append(hazardcategory)

        # Then technical recommendations

        hctra = HazardCategoryTechnicalRecommendationAssociation

        with open("data/technical_recommendations.csv", encoding="windows-1252") as csvfile:
            recommendations = csv.reader(csvfile, delimiter=",")
            next(recommendations, None)  # skip the headers
            for row in recommendations:
                technical_rec = TechnicalRecommendation(**{"text": row[0]})
                associations = technical_rec.hazardcategory_associations

                # the other columns are hazard category (type / level)
                for col_index in range(1, 28):
                    value = row[col_index]
                    if value != "" and value != "Y":
                        association = hctra(order=value)
                        association.hazardcategory = categories[col_index - 1]
                        associations.append(association)
                self.dbsession.add(technical_rec)

        # Climate change recommendations

        self.dbsession.query(ClimateChangeRecommendation).delete()

        # hazard types and corresponding columns
        hazard_types = [
            ("FL", 6),
            ("EQ", 7),
            ("CY", 8),
            ("CF", 9),
            ("DG", 10),
            ("TS", 11),
            ("VA", 12),
            ("LS", 13),
        ]

        with open("data/climate_change_recommendations.csv", encoding="windows-1252") as csvfile:
            countries = csv.reader(csvfile, delimiter=",")
            next(countries, None)  # skip the headers
            for row in countries:
                division = (
                    self.dbsession.query(AdministrativeDivision)
                    .filter(AdministrativeDivision.code == row[1])
                    .one_or_none()
                )

                if not division:
                    continue
                for hazard_type, column in hazard_types:
                    hazardtype = HazardType.get(self.dbsession, hazard_type)
                    text = row[column]
                    if text == "NA":
                        continue

                    climate_rec = (
                        self.dbsession.query(ClimateChangeRecommendation)
                        .filter(ClimateChangeRecommendation.text == text)
                        .filter(ClimateChangeRecommendation.hazardtype == hazardtype)
                        .first()
                    )
                    if climate_rec is None:
                        climate_rec = ClimateChangeRecommendation()
                        climate_rec.text = text
                        climate_rec.hazardtype = hazardtype
                        self.dbsession.add(climate_rec)

                    association = CcrAd(
                        administrativedivision=division, hazardtype=hazardtype
                    )

                    climate_rec.associations.append(association)


class ContactsImporter(BaseProcessor):

    def do_execute(self):
        self.dbsession.query(CAdHt).delete()
        self.dbsession.query(Contact).delete()

        """ Columns are:
         -  0
         -  1
         -  2 divivions code
         -  3 GAUL_CountryID
         -  4 WB country name
         -  5 Country Name
         -  6 is_IDA
         -  7 hazard type
         -  8 hazard mnemonic
         -  9 name 1   /—————————
         - 10 url 1   | Contact
         - 11 phone 1 | #1
         - 12 email 1  \—————————
         - 13 name 2   /—————————
         - 14 url 2   | Contact
         - 15 phone 2 | #2
         - 16 email 2  \—————————
         - 17 name 3   /—————————
         - 18 url 3   | Contact
         - 19 phone 3 | #3
         - 20 email 3  \—————————
        """

        filename = "data/hazardCountryList_Organizations_20170609.csv"
        with open(filename, encoding="windows-1252") as csvfile:
            contacts = csv.reader(csvfile, delimiter=",")
            next(contacts, None)  # skip the headers
            for row in contacts:

                if not row[2]:
                    continue
                division = (
                    self.dbsession.query(AdministrativeDivision)
                    .filter(AdministrativeDivision.code == int(row[2]))
                    .one_or_none()
                )
                if division is None:
                    continue

                hazardtype = (
                    self.dbsession.query(HazardType)
                    .filter(HazardType.mnemonic == str(row[8]))
                    .one_or_none()
                )
                if hazardtype is None:
                    continue

                for i in range(0, 3):
                    offset = i * 4
                    name = str(row[9 + offset])
                    url = str(row[10 + offset])
                    phone = str(row[11 + offset])
                    email = str(row[12 + offset])
                    if name == "" and url == "" and phone == "" and email == "":
                        continue

                    contact = (
                        self.dbsession.query(Contact)
                        .filter(Contact.name == name)
                        .filter(Contact.url == url)
                        .filter(Contact.phone == phone)
                        .filter(Contact.email == email)
                        .one_or_none()
                    )

                    if contact is None:
                        contact = Contact()
                        contact.name = name
                        contact.url = url
                        contact.phone = phone
                        contact.email = email
                        self.dbsession.add(contact)

                    association = CAdHt(
                        contact=contact,
                        administrativedivision=division,
                        hazardtype=hazardtype,
                    )
                    self.dbsession.add(association)
