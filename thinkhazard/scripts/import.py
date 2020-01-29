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

import sys
import os
import transaction
import csv
import subprocess

from sqlalchemy import engine_from_config
from pyramid.paster import setup_logging
from pyramid.scripts.common import parse_vars

from ..settings import load_full_settings

from ..models import (
    DBSession,
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


def usage(argv):
    cmd = os.path.basename(argv[0])
    print(
        (
            "usage: %s <config_uri> [var=value]\n"
            '(example: "%s development.ini")' % (cmd, cmd)
        )
    )
    sys.exit(1)


def import_admindivs(argv=sys.argv):
    """
    This script makes it so the database is populated with administrative
    divisions.
    """
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = load_full_settings(config_uri, options=options)

    engine = engine_from_config(settings, "sqlalchemy.")
    DBSession.configure(bind=engine)

    connection = DBSession.bind.connect()
    engine_url = DBSession.bind.url

    folder = options["folder"]
    for i in [0, 1, 2]:
        print("Importing GAUL data for level {}".format(i))
        print("This may take a while")
        trans = connection.begin()
        table_name = "g2015_2014_{}".format(i)
        shapefile = os.path.join(folder, table_name + "_upd270117.shp")
        p1 = subprocess.Popen(
            ["shp2pgsql", "-d", "-s", "4326", shapefile, table_name],
            stdout=subprocess.PIPE,
        )
        p2 = subprocess.Popen(["psql", "-d", str(engine_url)], stdin=p1.stdout)
        p2.communicate()
        trans.commit()

    trans = connection.begin()

    print("Creating administrative divs")
    connection.execute(
        """
WITH new_values (code, leveltype_id, name, parent_code, name_fr, name_es,
                 geom) AS (
    SELECT adm0_code, 1, adm0_name, NULL, fre, esp, geom
    FROM g2015_2014_0
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
    code, leveltype_id, name, name_fr, name_es, geom)
SELECT code, leveltype_id, name, name_fr, name_es, geom
FROM new_values
WHERE NOT EXISTS (SELECT 1
                  FROM upsert up
                  WHERE up.code = new_values.code);
"""
    )

    connection.execute(
        """
WITH new_values (code, leveltype_id, name, parent_code, geom) AS (
    SELECT adm1_code, 2, adm1_name, adm0_code, geom
    FROM g2015_2014_1
),
upsert AS (
    UPDATE datamart.administrativedivision ad
    SET name = nv.name,
        parent_code = nv.parent_code,
        geom = nv.geom
    FROM new_values nv
    WHERE ad.code = nv.code
    RETURNING ad.*
)
INSERT INTO datamart.administrativedivision (code, leveltype_id, name,
                                             parent_code, geom)
SELECT code, leveltype_id, name, parent_code, geom
FROM new_values
WHERE NOT EXISTS (SELECT 1
                  FROM upsert up
                  WHERE up.code = new_values.code);
"""
    )

    connection.execute(
        """
WITH new_values (code, leveltype_id, name, parent_code, geom) AS (
    SELECT adm2_code, 3, adm2_name, adm1_code, geom
    FROM g2015_2014_2
),
upsert AS (
    UPDATE datamart.administrativedivision ad
    SET name = nv.name,
        parent_code = nv.parent_code,
        geom = nv.geom
    FROM new_values nv
    WHERE ad.code = nv.code
    RETURNING ad.*
)
INSERT INTO datamart.administrativedivision (code, leveltype_id, name,
                                             parent_code, geom)
SELECT code, leveltype_id, name, parent_code, geom
FROM new_values
WHERE NOT EXISTS (SELECT 1
                  FROM upsert up
                  WHERE up.code = new_values.code);
"""
    )

    # Remove divisions that are in the db but not in the original shapefile
    # anymore
    connection.execute(
        """
DELETE FROM datamart.administrativedivision ad
WHERE ad.leveltype_id = 3 AND ad.code NOT IN (
    SELECT adm2_code
    FROM g2015_2014_2);
DELETE FROM datamart.administrativedivision ad
WHERE ad.leveltype_id = 2 AND ad.code NOT IN (
    SELECT adm1_code
    FROM g2015_2014_1);
DELETE FROM datamart.administrativedivision ad
WHERE ad.leveltype_id = 1 AND ad.code NOT IN (
    SELECT adm0_code
    FROM g2015_2014_0);
"""
    )

    # Remove climate change recommendations that are not linked to divisions
    # that don't exist anymore
    connection.execute(
        """
DELETE from datamart.rel_climatechangerecommendation_administrativedivision
WHERE administrativedivision_id NOT IN (
  SELECT id
  FROM datamart.administrativedivision
);
"""
    )

    # Finaly drop the temp table
    connection.execute(
        """
SELECT DropGeometryColumn('public', 'g2015_2014_0', 'geom');
DROP TABLE g2015_2014_0;
SELECT DropGeometryColumn('public', 'g2015_2014_1', 'geom');
DROP TABLE g2015_2014_1;
SELECT DropGeometryColumn('public', 'g2015_2014_2', 'geom');
DROP TABLE g2015_2014_2;
"""
    )

    trans.commit()

    print(
        "{} administrative divisions created".format(
            DBSession.query(AdministrativeDivision).count()
        )
    )


def import_recommendations(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = load_full_settings(config_uri, options=options)

    engine = engine_from_config(settings, "sqlalchemy.")
    DBSession.configure(bind=engine)

    with transaction.manager:

        DBSession.query(HazardCategoryTechnicalRecommendationAssociation).delete()
        DBSession.query(TechnicalRecommendation).delete()

        # First load general recommendations

        with open("data/general_recommendations.csv", "rb") as csvfile:
            recommendations = csv.reader(csvfile, delimiter=",")
            for row in recommendations:

                hazardcategory = (
                    DBSession.query(HazardCategory)
                    .join(HazardLevel)
                    .join(HazardType)
                    .filter(HazardLevel.mnemonic == row[1])
                    .filter(HazardType.mnemonic == row[0])
                    .one()
                )
                hazardcategory.general_recommendation = row[2]
                DBSession.add(hazardcategory)

        categories = []
        for type in ["EQ", "FL", "CY", "TS", "CF", "VA", "DG"]:
            for level in ["HIG", "MED", "LOW", "VLO"]:
                hazardcategory = (
                    DBSession.query(HazardCategory)
                    .join(HazardLevel)
                    .join(HazardType)
                    .filter(HazardLevel.mnemonic == level)
                    .filter(HazardType.mnemonic == type)
                    .one()
                )
                categories.append(hazardcategory)

        # Then technical recommendations

        hctra = HazardCategoryTechnicalRecommendationAssociation

        with open("data/technical_recommendations.csv", "rb") as csvfile:
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
                DBSession.add(technical_rec)

        # Climate change recommendations

        DBSession.query(ClimateChangeRecommendation).delete()

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

        with open("data/climate_change_recommendations.csv", "rb") as csvfile:
            countries = csv.reader(csvfile, delimiter=",")
            next(countries, None)  # skip the headers
            for row in countries:
                division = (
                    DBSession.query(AdministrativeDivision)
                    .filter(AdministrativeDivision.code == row[1])
                    .one_or_none()
                )

                if not division:
                    continue
                for hazard_type, column in hazard_types:
                    hazardtype = HazardType.get(hazard_type)
                    text = row[column]
                    if text == "NA":
                        continue

                    climate_rec = (
                        DBSession.query(ClimateChangeRecommendation)
                        .filter(ClimateChangeRecommendation.text == text)
                        .filter(ClimateChangeRecommendation.hazardtype == hazardtype)
                        .first()
                    )
                    if climate_rec is None:
                        climate_rec = ClimateChangeRecommendation()
                        climate_rec.text = text
                        climate_rec.hazardtype = hazardtype
                        DBSession.add(climate_rec)

                    association = CcrAd(
                        administrativedivision=division, hazardtype=hazardtype
                    )

                    climate_rec.associations.append(association)


def import_contacts(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)
    settings = load_full_settings(config_uri, options=options)

    engine = engine_from_config(settings, "sqlalchemy.")
    DBSession.configure(bind=engine)

    with transaction.manager:

        DBSession.query(CAdHt).delete()
        DBSession.query(Contact).delete()

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
        with open(filename, "rb") as csvfile:
            contacts = csv.reader(csvfile, delimiter=",")
            next(contacts, None)  # skip the headers
            for row in contacts:

                if not row[2]:
                    continue
                division = (
                    DBSession.query(AdministrativeDivision)
                    .filter(AdministrativeDivision.code == int(row[2]))
                    .one_or_none()
                )
                if division is None:
                    continue

                hazardtype = (
                    DBSession.query(HazardType)
                    .filter(HazardType.mnemonic == str(row[8]))
                    .one_or_none()
                )
                if hazardtype is None:
                    continue

                for i in range(0, 3):
                    offset = i * 4
                    name = str(row[9 + offset].decode("latin1"))
                    url = str(row[10 + offset].decode("latin1"))
                    phone = str(row[11 + offset].decode("latin1"))
                    email = str(row[12 + offset].decode("latin1"))
                    if name == "" and url == "" and phone == "" and email == "":
                        continue

                    contact = (
                        DBSession.query(Contact)
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
                        DBSession.add(contact)

                    association = CAdHt(
                        contact=contact,
                        administrativedivision=division,
                        hazardtype=hazardtype,
                    )
                    DBSession.add(association)
