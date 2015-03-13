Import
######

The shapefiles are first imported to an ``import`` schema, then the data is migrated to the production schema (named ``adminunits``).

In the following, we make the hypothesis that we already have a ``thinkhazard`` database with a postgis extension and an ``import`` schema.

If not::

    sudo -u postgres createdb -E UTF8 thinkhazard
    sudo -u postgres psql -d thinkhazard -c 'CREATE SCHEMA import;'
    sudo -u postgres psql -d thinkhazard -c 'CREATE EXTENSION postgis;’


Shapefiles import
=================

This does not take into account disputed area for now::

    shp2pgsql -g geometry -k -I -s 4326 Admin0_Polys.shp import.admin0 | sudo -u postgres psql -d thinkhazard
    shp2pgsql -g geometry -k -I -s 4326 Admin1_Polys.shp import.admin1 | sudo -u postgres psql -d thinkhazard
    shp2pgsql -g geometry -k -I -s 4326 Admin2_Polys.shp import.admin2 | sudo -u postgres psql -d thinkhazard


Data migration
==============

Use the following code, also available in the ``sql/etl.sql`` file::

    begin;

    insert into adminunits.admin0(id,         iso_code, gaul_code,    name,         geom) 
    select                        "OBJECTID", "ISO_A2", "WB_ADM0_CO", "WB_ADM0_NA", geometry from import.admin0;
    --INSERT 0 255

    insert into adminunits.admin1(id,         iso_code, gaul_code,    name,         admin0_gaul_code,   admin0_name,   geom) 
    select                        "OBJECTID", "ISO_A2", "WB_ADM1_CO", "WB_ADM1_NA", "WB_ADMO_CO",       "WB_ADM0_NA",  geometry from import.admin1;
    --INSERT 0 3447

    insert into adminunits.admin2(id,         iso_code, gaul_code,    name,         admin1_gaul_code, admin1_name,   admin0_gaul_code, admin0_name,  geom) 
    select                        "OBJECTID", "ISO_A2", "WB_ADM2_CO", "WB_ADM2_NA", "WB_ADM1_CO",     "WB_ADM1_NA",  "WB_ADM0_CO",     "WB_ADM0_NA",  geometry from import.admin2;
    --INSERT 0 37279

    select Populate_Geometry_Columns();

    commit;
