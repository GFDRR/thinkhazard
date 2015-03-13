begin;

create schema adminunits;
grant usage on schema adminunits to "www-data";

create table adminunits.admin0 (
  id integer primary key, -- OBJECTID
  iso_code varchar(2), -- ISO_A2
  gaul_code integer, -- WB_ADM0_CO
  name varchar(255), -- WB_ADM0_NA
  geom geometry -- geometry
);
create index admin0_name on adminunits.admin0 using btree (name);
create index admin0_gix on adminunits.admin0 using GIST (geom);
grant select on adminunits.admin0 to "www-data";


create table adminunits.admin1 (
  id integer primary key, -- OBJECTID
  iso_code varchar(2), -- ISO_A2
  gaul_code integer, -- WB_ADM1_CO
  name varchar(255), -- WB_ADM1_NA
  admin0_gaul_code integer, -- WB_ADM0_CO
  admin0_name varchar(255), -- WB_ADM0_NA
  geom geometry -- geometry
);
create index admin1_name on adminunits.admin1 using btree (name);
create index admin1_gix on adminunits.admin1 using GIST (geom);
grant select on adminunits.admin1 to "www-data";


create table adminunits.admin2 (
  id integer primary key, -- OBJECTID
  iso_code varchar(2), -- ISO_A2
  gaul_code integer, -- WB_ADM2_CO
  name varchar(255), -- WB_ADM2_NA
  admin0_gaul_code integer, -- WB_ADM0_CO
  admin0_name varchar(255), -- WB_ADM0_NA
  admin1_gaul_code integer, -- WB_ADM1_CO
  admin1_name varchar(255), -- WB_ADM1_NA
  geom geometry -- geometry
);
create index admin2_name on adminunits.admin2 using btree (name);
create index admin2_gix on adminunits.admin2 using GIST (geom);
grant select on adminunits.admin2 to "www-data";


commit;


