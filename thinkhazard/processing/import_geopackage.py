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

import importlib
import logging
import os

import geopandas as gpd
import sqlalchemy
from shapely.geometry import MultiPolygon, Polygon

from thinkhazard.lib.s3helper import S3Helper
from thinkhazard.models import (
    AdminLevelType,
    AdministrativeDivision,
    ClimateChangeRecAdministrativeDivisionAssociation,
    ContactAdministrativeDivisionHazardTypeAssociation,
    HazardCategory,
    HazardCategoryAdministrativeDivisionAssociation,
)
from thinkhazard.processing import BaseProcessor

LOG = logging.getLogger(__name__)

ADMDIV_MAPPINGS = {
    "COU": {
        "ISO_A3": "code",
        "GAUL_0": "gaul",
        "NAM_0": "name",
        "NAM_0_FR": "name_fr",
        "NAM_0_ES": "name_es",
        "NAM_0_EN": "name_en",
        "geometry": "geom",
    },
    "PRO": {
        "COD_1": "code",
        "NAM_1": "name",
        "ISO_A3": "parent_code",
        "NAM_1_FR": "name_fr",
        "NAM_1_ES": "name_es",
        "NAM_1_EN": "name_en",
        "geometry": "geom",
    },
    "REG": {
        "COD_2": "code",
        "NAM_2": "name",
        "COD_1": "parent_code",
        "geometry": "geom",
    },
    "URB": {
        "COD_URB": "code",
        "NAM_URB": "name",
        "COD_2": "parent_code",
        "NAM_URB_FR": "name_fr",
        "NAM_URB_ES": "name_es",
        "NAM_URB_EN": "name_en",
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
    "TC_Hazard_score": "TC",
    "VO_Hazard_score": "VA",  # VO in GeoPackage = VA in DB
    "EH_Hazard_score": "EH",
    "TS_Hazard_score": "TS",
    "WF_Hazard_score": "WF",
}

CODE_COLUMNS = {
    "COU": "ISO_A3",
    "PRO": "COD_1",
    "REG": "COD_2",
    "URB": "COD_URB",
}


def to_multipolygon(geom):
    if geom is None:
        return None
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    return geom


class GeopackageImporter(BaseProcessor):
    """
    Imports administrative divisions and their hazard scores from a GeoPackage.

    This class handles complete administrative data import following a structured workflow
    for optimal performance and data consistency.

    **Process Overview:**
    1. **Data Source Preparation:** Download from S3 or use local GeoPackage file
    2. **Data Reading:** Load ADM2 and Urban layers from GeoPackage
    3. **Data Validation:** Verify uniqueness, handle null values, remove orphaned territories
    4. **Boundary Dissolution:** Generate ADM1 and ADM0 levels from ADM2 data
    5. **Database Optimization:** Drop foreign key constraints for bulk operations
    6. **Data Clearing:** Remove existing relationships (hazard scores, regions, processing outputs)
    7. **Administrative Import:** Bulk insert new divisions with upsert strategy
    8. **Hazard Score Import:** Create hazard-division associations with score mapping
    9. **Constraint Recreation:** Restore foreign keys and clean orphaned relationships
    10. **Finalization:** Update missing translations and compute simplified geometries

    *S3 Support:*
    - Automatic download from s3:// URLs to local temporary storage

    *Data Validation:*
    - Code uniqueness verification across all administrative levels
    - Parent-child relationship validation
    - Detection and removal of orphaned territories (territories without valid sovereign)
    - Automatic cleanup of null values in required fields

    *Boundary Dissolution:*
    - ADM2: Direct source data from GeoPackage layers
    - ADM1: Dissolved from ADM2 by (ISO_A3, COD_1) groups with aggregated maximum hazard scores
    - ADM0: Dissolved from ADM1 by ISO_A3 with aggregated maximum hazard scores
    - Special territory handling: WB_STATUS="Territory" uses SOVEREIGN for parent relationships
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geopackage_path: str | None = None
        self.gdf_adm2: gpd.GeoDataFrame | None = None
        self.gdf_adm1: gpd.GeoDataFrame | None = None
        self.gdf_adm0: gpd.GeoDataFrame | None = None
        self.gdf_urban: gpd.GeoDataFrame | None = None

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
        if geopackage_path is None:
            raise ValueError("Geopackage path is required")

        if geopackage_path.startswith("s3://"):
            LOG.info(f"S3 URL detected: {geopackage_path}")
            self.geopackage_path = self.download_from_s3(geopackage_path)
        else:
            self.geopackage_path = geopackage_path

        self.read_adm2()
        self.read_urban()

        self.validate()

        self.dissolve()

        self.clear_all_data()
        self.drop_foreign_keys()
        self.import_admindivs()
        self.recreate_foreign_keys()

        self.import_hazard_scores()

        self.finish()

    def download_from_s3(self, s3_url):
        """Download geopackage from S3 URL and return local path."""
        LOG.info(f"Downloading geopackage from S3: {s3_url}")

        if not s3_url.startswith("s3://"):
            raise ValueError(f"Invalid S3 URL format: {s3_url}")

        path_part = s3_url[5:]  # Remove 's3://'
        bucket, object_name = path_part.split("/", 1)

        s3_helper = S3Helper(self.settings)
        local_path = "/tmp/hazardsets/admindivs.gpkg"

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        if os.path.exists(local_path):
            os.unlink(local_path)

        s3_helper.download_file(object_name, local_path)

        LOG.info(f"Successfully downloaded geopackage to: {local_path}")
        return local_path

    def read_adm2(self):
        if not os.path.isfile(self.geopackage_path):
            raise FileNotFoundError(
                f"Geopackage file not found: {self.geopackage_path}"
            )

        LOG.info("Reading ADM2 source: %s", self.geopackage_path)
        gdf_adm2 = gpd.read_file(self.geopackage_path, layer="ADM2", engine="pyogrio")

        LOG.info("Existing columns: %s", list(gdf_adm2.columns))

        self.gdf_adm2 = gdf_adm2

    def read_urban(self):
        LOG.info("Reading Urban source: %s", self.geopackage_path)
        gdf_urban = gpd.read_file(self.geopackage_path, layer="URB", engine="pyogrio")

        gdf_urban["COD_URB"] = gdf_urban["COD_URB"].astype(str)

        LOG.info("Existing columns: %s", list(gdf_urban.columns))
        LOG.info("Urban Count: %d", len(gdf_urban))

        # gdf_urban = gdf_urban.head(100)

        self.gdf_urban = gdf_urban

    def validate(self):

        def analyse_unicity(key_column, value_column, action_msg=None, raise_error=False):
            """Log warning if we have multiple value for the same key"""
            counts = self.gdf_adm2.groupby(key_column)[value_column].agg(
                lambda x: set(x)
            )
            violations = counts[counts.apply(len) > 1]
            if not violations.empty:
                msg = f"We found multiple {value_column} for the same {key_column}:"
                for key, values in violations.items():
                    msg = msg + f"\n{key}: {list(values)}"
                if action_msg is None:
                    action_msg = "We will keep only the most used one."
                if action_msg != "":
                    msg = msg + f"\n{action_msg}"
                if raise_error:
                    raise Exception(msg)
                LOG.warning(msg)

        analyse_unicity("ISO_A3", "NAM_0")
        analyse_unicity("ISO_A3", "GAUL_0")
        analyse_unicity("GAUL_0", "ISO_A3", action_msg="")
        analyse_unicity("COD_1", "ISO_A3", True)
        analyse_unicity("COD_1", "NAM_1")
        # analyse_unicity("ADM2CD_c", "ADM1CD_c", True)

        null_mask = self.gdf_adm2["NAM_2"].isnull()
        null_codes = set(self.gdf_adm2.loc[null_mask, "COD_2"])
        if null_codes:
            null_iso = sorted(self.gdf_adm2.loc[null_mask, "ISO_A3"].dropna().unique())
            LOG.warning(
                "Column NAM_2 contains null values; dropping %d rows (ISO_A3: %s)",
                len(null_codes),
                ", ".join(null_iso) if null_iso else "unknown",
            )
            self.gdf_adm2 = self.gdf_adm2[~null_mask]

            if self.gdf_urban is not None:
                before = len(self.gdf_urban)
                self.gdf_urban = self.gdf_urban[
                    ~self.gdf_urban["COD_2"].isin(null_codes)
                ]
                LOG.info(
                    "Dropped %d urban rows referencing removed ADM2 codes",
                    before - len(self.gdf_urban),
                )

        if self.gdf_urban is not None:
            if not self.gdf_urban["COD_URB"].is_unique:
                duplicates = self.gdf_urban[
                    self.gdf_urban["COD_URB"].duplicated(keep=False)
                ]
                dup_list = duplicates["COD_URB"].tolist()
                raise Exception(f"COD_URB must be unique. Duplicates: {dup_list}")

            if (
                "NAM_URB" in self.gdf_urban.columns
                and self.gdf_urban["NAM_URB"].isnull().any()
            ):
                LOG.warning(
                    "Column NAM_URB contains null values, those lines will be ignored."
                )
                self.gdf_urban = self.gdf_urban[self.gdf_urban["NAM_URB"].notnull()]

        # Find ISO_A3 codes where ALL rows are territories (WB_STATUS="Territory")
        # These will never produce an ADM0, so their SOVEREIGN parent won't exist
        territory_only_iso = self.gdf_adm2.groupby("ISO_A3")["WB_STATUS"].apply(
            lambda x: (x == "Territory").all()
        )
        territory_only_codes = set(territory_only_iso[territory_only_iso].index)
        if territory_only_codes:
            # Check if their SOVEREIGN is also territory-only (orphan)
            orphan_sovereigns = set()
            for code in territory_only_codes:
                sovereign = self.gdf_adm2.loc[
                    self.gdf_adm2["ISO_A3"] == code, "SOVEREIGN"
                ].iloc[0]
                # If sovereign is also territory-only or doesn't exist, it's orphan
                if sovereign in territory_only_codes or sovereign not in set(
                    self.gdf_adm2["ISO_A3"]
                ):
                    orphan_sovereigns.add(code)

            if orphan_sovereigns:
                LOG.warning(
                    "Dropping ISO_A3 codes that are territory-only with no valid "
                    "sovereign parent:"
                )
                for code in sorted(orphan_sovereigns):
                    sovereign = self.gdf_adm2.loc[
                        self.gdf_adm2["ISO_A3"] == code, "SOVEREIGN"
                    ].iloc[0]
                    LOG.warning("  - %s (SOVEREIGN=%s)", code, sovereign)

                orphan_mask = self.gdf_adm2["ISO_A3"].isin(orphan_sovereigns)
                removed_adm2_codes = set(self.gdf_adm2.loc[orphan_mask, "COD_2"])
                self.gdf_adm2 = self.gdf_adm2[~orphan_mask]

                # Also filter Urban records referencing removed ADM2
                if self.gdf_urban is not None:
                    urban_orphan_mask = self.gdf_urban["COD_2"].isin(removed_adm2_codes)
                    if urban_orphan_mask.any():
                        LOG.warning(
                            "Dropping %d Urban records in orphan territories",
                            urban_orphan_mask.sum(),
                        )
                        self.gdf_urban = self.gdf_urban[~urban_orphan_mask]

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
            by=["ISO_A3", "COD_1"],
            aggfunc={
                "GAUL_0": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0_FR": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0_ES": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0_EN": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_1": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_1_FR": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_1_ES": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_1_EN": lambda x: x.mode()[0] if not x.mode().empty else None,
                "SOVEREIGN": "first",
                "WB_STATUS": "first",
                **{col: "max" for col in hazard_score_cols},
            },
            as_index=False,
        )
        self.gdf_adm1["geometry"] = self.gdf_adm1.geometry.buffer(0)

        territory_mask = self.gdf_adm1["WB_STATUS"] == "Territory"
        self.gdf_adm1.loc[territory_mask, "ISO_A3"] = self.gdf_adm1.loc[
            territory_mask, "SOVEREIGN"
        ]

        LOG.info("Extracting ADM0 boundaries...")
        gdf_adm1_sovereign = self.gdf_adm1[self.gdf_adm1["WB_STATUS"] != "Territory"]
        self.gdf_adm0 = gdf_adm1_sovereign.dissolve(
            by="ISO_A3",
            aggfunc={
                "GAUL_0": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0_FR": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0_ES": lambda x: x.mode()[0] if not x.mode().empty else None,
                "NAM_0_EN": lambda x: x.mode()[0] if not x.mode().empty else None,
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
        # connection.execute(
        #     sqlalchemy.text(
        #         "ALTER TABLE datamart.rel_hazardcategory_administrativedivision "
        #         "DROP CONSTRAINT IF EXISTS rel_hazardcategory_administrativ_administrativedivision_id_fkey"
        #     )
        # )
        # connection.execute(
        #     sqlalchemy.text(
        #         "ALTER TABLE datamart.rel_region_administrativedivision "
        #         "DROP CONSTRAINT IF EXISTS rel_region_administrativedivisi_administrativedivision_id_fkey"
        #     )
        # )
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
        # connection.execute(
        #     sqlalchemy.text(
        #         "ALTER TABLE processing.output "
        #         "DROP CONSTRAINT IF EXISTS output_admin_id_fkey"
        #     )
        # )

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
            sqlalchemy.text("DELETE FROM datamart.rel_region_administrativedivision")
        )
        connection.execute(
            sqlalchemy.text("DELETE FROM datamart.rel_hazardcategory_administrativedivision")
        )
        connection.execute(
            sqlalchemy.text("DELETE FROM processing.output")
        )
        # connection.execute(
        #     sqlalchemy.text("DELETE FROM datamart.administrativedivision")
        # )

    def delete_orphans(self, child_class):
        from sqlalchemy import select, func, exists, delete

        condition = ~exists().where(
            child_class.administrativedivision_id
            == AdministrativeDivision.id
        )

        total = self.dbsession.scalars(
            select(func.count())
            .select_from(child_class)
        ).one()

        orphans = self.dbsession.scalars(
            select(func.count())
            .select_from(child_class)
            .where(condition)
        ).one()

        if orphans > 0:
            LOG.warning(
                "%s / %s orphan %s will be lost.",
                orphans,
                total,
                child_class.__name__,
            )

            self.dbsession.execute(
                delete(child_class).where(condition)
                .execution_options(synchronize_session=False)
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

        # connection.execute(
        #     sqlalchemy.text(
        #         "ALTER TABLE datamart.rel_hazardcategory_administrativedivision "
        #         "ADD CONSTRAINT rel_hazardcategory_administrativ_administrativedivision_id_fkey "
        #         "FOREIGN KEY (administrativedivision_id) "
        #         "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
        #     )
        # )

        # connection.execute(
        #     sqlalchemy.text(
        #         "ALTER TABLE datamart.rel_region_administrativedivision "
        #         "ADD CONSTRAINT rel_region_administrativedivisi_administrativedivision_id_fkey "
        #         "FOREIGN KEY (administrativedivision_id) "
        #         "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
        #     )
        # )

        self.delete_orphans(ClimateChangeRecAdministrativeDivisionAssociation)
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_climatechangerecommendation_administrativedivision "
                "ADD CONSTRAINT rel_climatechangerecommendation_administrativedivision_id_fkey "
                "FOREIGN KEY (administrativedivision_id) "
                "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
            )
        )

        self.delete_orphans(ContactAdministrativeDivisionHazardTypeAssociation)
        connection.execute(
            sqlalchemy.text(
                "ALTER TABLE datamart.rel_contact_administrativedivision_hazardtype "
                "ADD CONSTRAINT rel_contact_administrativedivisi_administrativedivision_id_fkey "
                "FOREIGN KEY (administrativedivision_id) "
                "REFERENCES datamart.administrativedivision(id)"
            )
        )

        # connection.execute(
        #     sqlalchemy.text(
        #         "ALTER TABLE processing.output "
        #         "ADD CONSTRAINT output_admin_id_fkey "
        #         "FOREIGN KEY (admin_id) "
        #         "REFERENCES datamart.administrativedivision(id) ON DELETE CASCADE"
        #     )
        # )

    def import_admindivs(self):
        connection = self.dbsession.connection()

        # Create temporary schema
        # because geopandas.to_postgis does not support append in pg_temp
        connection.execute(
            sqlalchemy.text(
                """
                CREATE SCHEMA IF NOT EXISTS temp;
                CREATE TABLE temp.administrativedivision (
                    code character varying NOT NULL PRIMARY KEY,
                    gaul integer,
                    leveltype_id integer NOT NULL,
                    name character varying NOT NULL,
                    parent_code character varying,
                    geom public.geometry(MultiPolygon,4326),
                    name_fr character varying,
                    name_es character varying,
                    name_en character varying,
                    geom_simplified public.geometry(MultiPolygon,3857),
                    geom_simplified_for_parent public.geometry(MultiPolygon,3857)
                );
                """
            )
        )

        LOG.info("Importing ADM0")
        self.import_admdiv_level("COU", self.gdf_adm0)

        LOG.info("Importing ADM1")
        self.import_admdiv_level("PRO", self.gdf_adm1)

        LOG.info("Importing ADM2")
        self.import_admdiv_level("REG", self.gdf_adm2)

        LOG.info("Importing Urban")
        self.import_admdiv_level("URB", self.gdf_urban)

        LOG.info("Handling GAUL")
        self.handle_gaul()

        LOG.info("Updating table datamart.administrativedivision")
        self.upsert_admindiv()

        LOG.info("Cleaning table datamart.administrativedivision")
        self.clean_admindivs()

        connection.execute(
            sqlalchemy.text(
                """
                DROP SCHEMA temp CASCADE;
                """
            )
        )

    def import_admdiv_level(self, level_mnemonic: str, gdf: gpd.GeoDataFrame):
        """Import one level of new administrative divisions in temporary table."""

        level = AdminLevelType.get(self.dbsession, level_mnemonic)

        mapping = ADMDIV_MAPPINGS[level_mnemonic]

        gdf = gdf[mapping.keys()]
        gdf = gdf.rename(columns=mapping)
        gdf = gdf.set_geometry("geom")

        gdf["leveltype_id"] = level.id

        gdf["geom"] = gdf["geom"].apply(to_multipolygon)

        gdf.to_postgis(
            schema="temp",
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

    def handle_gaul(self):
        """
        Update code using GAUL on admin0
        Should be useful only on first import
        Could be removed at sometime
        """
        self.dbsession.connection().execute(
            sqlalchemy.text(
                """
UPDATE datamart.administrativedivision dest
SET code = src.code
FROM temp.administrativedivision src
WHERE dest.code = src.gaul::text
    AND src.leveltype_id = 1
    AND dest.leveltype_id = 1
                """
            )
        )

    def upsert_admindiv(self):
        """
        Make an upsert of new administrative divisions based on code field.
        """
        self.dbsession.connection().execute(
            sqlalchemy.text(
                """
INSERT INTO datamart.administrativedivision (
        code,
        gaul,
        leveltype_id,
        name,
        parent_code,
        name_fr,
        name_es,
        name_en,
        geom
    )
    SELECT
        code,
        gaul,
        leveltype_id,
        name,
        parent_code,
        name_fr,
        name_es,
        name_en,
        geom
    FROM temp.administrativedivision
ON CONFLICT (code)
DO
    UPDATE
        SET gaul = EXCLUDED.gaul,
            leveltype_id = EXCLUDED.leveltype_id,
            name = EXCLUDED.name,
            parent_code = EXCLUDED.parent_code,
            name_fr = EXCLUDED.name_fr,
            name_es = EXCLUDED.name_es,
            name_en = EXCLUDED.name_en,
            geom = EXCLUDED.geom
;
                """
            )
        )

#     def handle_gaul(self):
#         """
#         Update relations when migrating from GAUL to new administrative divisions.
#         Should be useful only once.
#         Could be removed after first import.
#         """
#         connection = self.dbsession.connection()
#         connection.execute(
#             sqlalchemy.text(
#                 """
# -- Handle GAUL
# UPDATE datamart.rel_climatechangerecommendation_administrativedivision rel
# SET administrativedivision_id = new_id
# FROM (
#     SELECT
#         old.id AS old_id,
#         new.id AS new_id
#     FROM datamart.administrativedivision old
#     LEFT JOIN datamart.administrativedivision new
#         ON old.code = new.gaul::text
#     WHERE old.leveltype_id = 1
#     AND new.leveltype_id = 1
# ) AS map
# WHERE map.old_id = rel.administrativedivision_id;

# UPDATE datamart.rel_contact_administrativedivision_hazardtype rel
# SET administrativedivision_id = new_id
# FROM (
#     SELECT
#         old.id AS old_id,
#         new.id AS new_id
#     FROM datamart.administrativedivision old
#     LEFT JOIN datamart.administrativedivision new
#         ON old.code = new.gaul::text
#     WHERE old.leveltype_id = 1
#     AND new.leveltype_id = 1
# ) AS map
# WHERE map.old_id = rel.administrativedivision_id;
#                 """
#             )
#         )

    def clean_admindivs(self):
        """
        Delete administrative divisions which are not in new dataset.
        """
        connection = self.dbsession.connection()
        connection.execute(
            sqlalchemy.text(
                """
ANALYZE datamart.administrativedivision;
ANALYZE temp.administrativedivision;

DELETE FROM datamart.administrativedivision dest
WHERE NOT EXISTS (
    SELECT 1
    FROM temp.administrativedivision src
    WHERE src.code = dest.code
);
                """
            )
        )

    def import_hazard_scores(self):
        LOG.info("Importing hazard scores for ADM0")
        self.import_hazard_scores_level("COU", self.gdf_adm0)
        LOG.info("Importing hazard scores for ADM1")
        self.import_hazard_scores_level("PRO", self.gdf_adm1)
        LOG.info("Importing hazard scores for ADM2")
        self.import_hazard_scores_level("REG", self.gdf_adm2)
        LOG.info("Importing hazard scores for Urban")
        self.import_hazard_scores_level("URB", self.gdf_urban)

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

    def finish(self):
        self.dbsession.connection().execute(
            sqlalchemy.text(
                """
UPDATE datamart.administrativedivision
SET name_fr = coalesce(name_fr, name),
    name_es = coalesce(name_es, name);
"""
            )
        )

        # Without this, the execution time of simplify can explode.
        self.dbsession.connection().execute(sqlalchemy.text("ANALYZE;"))

        LOG.info("Simplifying geometries")
        sql = importlib.resources.read_text("thinkhazard.scripts", "simplify.sql")
        self.dbsession.connection().execute(sqlalchemy.text(sql))
