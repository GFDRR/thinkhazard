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
import logging

import geopandas as gpd
import sqlalchemy
from shapely.geometry import MultiPolygon, Polygon

from thinkhazard.processing import BaseProcessor
from thinkhazard.models import (
    AdminLevelType,
    AdministrativeDivision,
    HazardCategory,
    HazardCategoryAdministrativeDivisionAssociation,
)

LOG = logging.getLogger(__name__)

ADMDIV_MAPPINGS = {
    "COU": {
        "ISO_A3": "code",
        "NAM_0": "name",
        "geometry": "geom",
    },
    "PRO": {
        "ADM1CD_c": "code",
        "NAM_1": "name",
        "ISO_A3": "parent_code",
        "geometry": "geom",
    },
    "REG": {
        "ADM2CD_c": "code",
        "NAM_2": "name",
        "ADM1CD_c": "parent_code",
        "geometry": "geom",
    },
}

SCORE_TO_LEVEL = {
    0: "VLO",
    1: "LOW",
    2: "MED",
    3: "HIG",
}

HAZARD_SCORE_COLUMNS = {
    "LS_Hazard_score": "LS",
    "EQ_Hazard_score": "EQ",
    "TC_Hazard_score": "CY",  # TC in GeoPackage = CY in DB
    "VO_Hazard_score": "VA",  # VO in GeoPackage = VA in DB
    "EH_Hazard_score": "EH",
    "TS_Hazard_score": "TS",
    "WF_Hazard_score": "WF",
}

CODE_COLUMNS = {
    "COU": "ISO_A3",
    "PRO": "ADM1CD_c",
    "REG": "ADM2CD_c",
}


def to_multipolygon(geom):
    if geom is None:
        return None
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    return geom


class GeopackageImporter(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geopackage_path: str | None = None
        self.gdf_adm2: gpd.GeoDataFrame | None = None
        self.gdf_adm1: gpd.GeoDataFrame | None = None
        self.gdf_adm0: gpd.GeoDataFrame | None = None

    @staticmethod
    def argument_parser():
        parser = BaseProcessor.argument_parser()
        parser.add_argument(
            "--geopackage-path",
            dest="geopackage_path",
            type=str,
            required=False,
            default=None,
            help="Path to the geopackage file to import",
        )
        return parser

    def do_execute(self, geopackage_path):
        self.read_adm2(geopackage_path)
        self.validate()
        self.dissolve()

        self.drop_foreign_keys()

        self.clear_all_data()

        self.import_admindivs()
        self.import_hazard_scores()

        self.recreate_foreign_keys()

    def read_adm2(self, geopackage_path):
        if geopackage_path is None:
            raise ValueError("Geopackage path is required")

        self.geopackage_path = geopackage_path

        if not os.path.isfile(self.geopackage_path):
            raise FileNotFoundError(
                f"Geopackage file not found: {self.geopackage_path}"
            )

        LOG.info("Reading ADM2 source: %s", self.geopackage_path)
        gdf_adm2 = gpd.read_file(self.geopackage_path, engine="pyogrio")

        LOG.info("Existing columns: %s", list(gdf_adm2.columns))

        self.gdf_adm2 = gdf_adm2

    def validate(self):

        def analyse_unicity(key_column, value_column, raise_error=False):
            """Log warning if we have multiple value for the same key"""
            counts = self.gdf_adm2.groupby(key_column)[value_column].agg(
                lambda x: set(x)
            )
            violations = counts[counts.apply(len) > 1]
            if not violations.empty:
                msg = f"We found multiple {value_column} for the same {key_column}:"
                for key, values in violations.items():
                    msg = msg + "\n" + f"{key}: {list(values)}"
                msg = msg + "We will keep only the most used one."
                if raise_error:
                    raise Exception(msg)
                LOG.warning(msg)

        analyse_unicity("ISO_A3", "NAM_0")
        analyse_unicity("ADM1CD_c", "ISO_A3", True)
        analyse_unicity("ADM1CD_c", "NAM_1")
        # analyse_unicity("ADM2CD_c", "ADM1CD_c", True)

        if self.gdf_adm2["NAM_2"].isnull().any():
            LOG.warning(
                "Column NAM_2 contains null values, those lines will be ignored."
            )
            self.gdf_adm2 = self.gdf_adm2[self.gdf_adm2["NAM_2"].notnull()]

    def dissolve(self):
        hazard_score_cols = [
            "LS_Hazard_score",
            "EQ_Hazard_score",
            "TC_Hazard_score",
            "VO_Hazard_score",
            "EH_Hazard_score",
            "TS_Hazard_score",
            "WF_Hazard_score",
        ]

        LOG.info("Extracting ADM1 boundaries...")
        self.gdf_adm1 = self.gdf_adm2.dissolve(
            by=["ISO_A3", "ADM1CD_c"],
            aggfunc={
                "NAM_0": lambda x: list(x.mode()),
                "NAM_1": lambda x: list(x.mode()),
                **{col: "max" for col in hazard_score_cols},
            },
            as_index=False,
        )
        self.gdf_adm1["geometry"] = self.gdf_adm1.geometry.buffer(0)

        LOG.info("Extracting ADM0 boundaries...")
        self.gdf_adm0 = self.gdf_adm1.dissolve(
            by="ISO_A3",
            aggfunc={
                "NAM_0": lambda x: list(x.mode()),
                **{col: "max" for col in hazard_score_cols},
            },
            as_index=False,
        )
        self.gdf_adm0["geometry"] = self.gdf_adm0.geometry.buffer(0)

        LOG.info("Processing Complete.")
        LOG.info("ADM2 Count: %d", len(self.gdf_adm2))
        LOG.info("ADM1 Count: %d", len(self.gdf_adm1))
        LOG.info("ADM0 Count: %d", len(self.gdf_adm0))

    def drop_foreign_keys(self):
        """Drop FK constraints temporarily for fast bulk import."""
        LOG.info("Dropping foreign key constraints...")
        connection = self.dbsession.connection()

        # All FKs that reference administrativedivision (from models.py):
        # 1. administrativedivision.parent_code -> administrativedivision.code
        # 2. rel_hazardcategory_administrativedivision.administrativedivision_id
        # 3. rel_region_administrativedivision.administrativedivision_id
        # 4. rel_climatechangerecommendation_administrativedivision.administrativedivision_id
        # 5. rel_contact_administrativedivision_hazardtype.administrativedivision_id
        # 6. processing.output.admin_id

        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.administrativedivision "
                "DROP CONSTRAINT IF EXISTS administrativedivision_parent_code_fkey"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_hazardcategory_administrativedivision "
                "DROP CONSTRAINT IF EXISTS rel_hazardcategory_administrativ_administrativedivision_id_fkey"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_region_administrativedivision "
                "DROP CONSTRAINT IF EXISTS rel_region_administrativedivisi_administrativedivision_id_fkey"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_climatechangerecommendation_administrativedivision "
                "DROP CONSTRAINT IF EXISTS rel_climatechangerecommendation_administrativedivision_id_fkey"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_contact_administrativedivision_hazardtype "
                "DROP CONSTRAINT IF EXISTS rel_contact_administrativedivisi_administrativedivision_id_fkey"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE processing.output "
                "DROP CONSTRAINT IF EXISTS output_admin_id_fkey"
            )
        )

    def clear_all_data(self):
        """Clear all existing administrative division and related data."""
        LOG.info("Clearing existing data...")
        connection = self.dbsession.connection()

        # TRUNCATE with CASCADE automatically clears all dependent tables:
        # - rel_hazardcategory_administrativedivision
        # - rel_region_administrativedivision
        # - rel_climatechangerecommendation_administrativedivision
        # - rel_contact_administrativedivision_hazardtype
        # - processing.output
        connection.execute(
            sqlalchemy.text("TRUNCATE datamart.administrativedivision CASCADE")
        )

    def recreate_foreign_keys(self):
        """Recreate FK constraints after bulk import."""
        LOG.info("Recreating foreign key constraints...")
        connection = self.dbsession.connection()

        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.administrativedivision "
                "ADD CONSTRAINT administrativedivision_parent_code_fkey "
                "FOREIGN KEY (parent_code) REFERENCES datamart.administrativedivision(code)"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_hazardcategory_administrativedivision "
                "ADD CONSTRAINT rel_hazardcategory_administrativ_administrativedivision_id_fkey "
                "FOREIGN KEY (administrativedivision_id) "
                "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_region_administrativedivision "
                "ADD CONSTRAINT rel_region_administrativedivisi_administrativedivision_id_fkey "
                "FOREIGN KEY (administrativedivision_id) "
                "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_climatechangerecommendation_administrativedivision "
                "ADD CONSTRAINT rel_climatechangerecommendation_administrativedivision_id_fkey "
                "FOREIGN KEY (administrativedivision_id) "
                "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_contact_administrativedivision_hazardtype "
                "ADD CONSTRAINT rel_contact_administrativedivisi_administrativedivision_id_fkey "
                "FOREIGN KEY (administrativedivision_id) "
                "REFERENCES datamart.administrativedivision(id)"
            )
        )
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE processing.output "
                "ADD CONSTRAINT output_admin_id_fkey "
                "FOREIGN KEY (admin_id) "
                "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
            )
        )

    def import_admindivs(self):
        LOG.info("Importing ADM0")
        self.import_admdiv_level("COU", self.gdf_adm0)

        LOG.info("Importing ADM1")
        self.import_admdiv_level("PRO", self.gdf_adm1)

        LOG.info("Importing ADM2")
        self.import_admdiv_level("REG", self.gdf_adm2)

    def import_admdiv_level(self, level_mnemonic: str, gdf: gpd.GeoDataFrame):
        level = AdminLevelType.get(self.dbsession, level_mnemonic)

        mapping = ADMDIV_MAPPINGS[level_mnemonic]

        gdf = gdf[mapping.keys()]
        gdf = gdf.rename(columns=mapping)
        gdf = gdf.set_geometry("geom")

        gdf["leveltype_id"] = level.id

        gdf["geom"] = gdf["geom"].apply(to_multipolygon)

        gdf.to_postgis(
            schema=AdministrativeDivision.__table__.schema,
            name=AdministrativeDivision.__table__.name,
            con=self.dbsession.connection(),
            if_exists="append",
            index=False,
        )

        # from geoalchemy2.shape import from_shape
        # self.dbsession.bulk_save_objects([
        #     AdministrativeDivision(
        #         code=row['code'],
        #         name=row['name'],
        #         leveltype_id=level.id,
        #         # name_fr,
        #         # name_es,
        #         parent_code=row.get('parent_code'),
        #         geom=from_shape(to_multipolygon(row['geom'])),
        #         # geom_simplified,
        #         # geom_simplified_for_parent,
        #     )
        #     for _, row in gdf.iterrows()
        # ])

    def import_hazard_scores(self):
        LOG.info("Importing hazard scores for ADM0")
        self.import_hazard_scores_level("COU", self.gdf_adm0)
        LOG.info("Importing hazard scores for ADM1")
        self.import_hazard_scores_level("PRO", self.gdf_adm1)
        LOG.info("Importing hazard scores for ADM2")
        self.import_hazard_scores_level("REG", self.gdf_adm2)

    def import_hazard_scores_level(
        self, admin_level_mnemonic: str, gdf: gpd.GeoDataFrame
    ):
        code_column = CODE_COLUMNS[admin_level_mnemonic]

        expected_columns = {code_column, *HAZARD_SCORE_COLUMNS.keys()}
        missing_columns = expected_columns - set(gdf.columns)
        if missing_columns:
            LOG.warning(
                "Missing columns for %s: %s; skipping",
                admin_level_mnemonic,
                ", ".join(sorted(missing_columns)),
            )
            return

        level = AdminLevelType.get(self.dbsession, admin_level_mnemonic)
        admin_ids_by_code = {
            ad.code: ad.id
            for ad in self.dbsession.query(AdministrativeDivision).filter(
                AdministrativeDivision.leveltype_id == level.id
            )
        }

        hazard_category_cache: dict[tuple[str, str], HazardCategory | None] = {}
        hazard_associations: list[HazardCategoryAdministrativeDivisionAssociation] = []
        missing_admin_codes: set[str] = set()

        for row in gdf.itertuples(index=False):
            admin_code = getattr(row, code_column)
            admin_id = admin_ids_by_code.get(admin_code)
            if admin_id is None:
                missing_admin_codes.add(admin_code)
                continue

            for gpkg_col, hazard_mnemonic in HAZARD_SCORE_COLUMNS.items():
                score = getattr(row, gpkg_col)
                hazard_level_mnemonic = SCORE_TO_LEVEL.get(score)
                if hazard_level_mnemonic is None:
                    continue

                cache_key = (hazard_mnemonic, hazard_level_mnemonic)
                if cache_key not in hazard_category_cache:
                    hazard_category_cache[cache_key] = HazardCategory.get(
                        self.dbsession, hazard_mnemonic, hazard_level_mnemonic
                    )
                hazard_category = hazard_category_cache[cache_key]
                if hazard_category is None:
                    LOG.warning(
                        "HazardCategory not found: %s/%s",
                        hazard_mnemonic,
                        hazard_level_mnemonic,
                    )
                    continue

                hazard_associations.append(
                    HazardCategoryAdministrativeDivisionAssociation(
                        administrativedivision_id=admin_id,
                        hazardcategory_id=hazard_category.id,
                    )
                )

        if hazard_associations:
            self.dbsession.bulk_save_objects(hazard_associations, return_defaults=False)

        if missing_admin_codes:
            LOG.warning(
                "Admin divisions not found for %s codes: %s",
                admin_level_mnemonic,
                ", ".join(sorted(missing_admin_codes)),
            )

        LOG.info(
            "Created %d hazard associations for %s",
            len(hazard_associations),
            admin_level_mnemonic,
        )
