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




