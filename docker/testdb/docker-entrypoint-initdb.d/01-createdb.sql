CREATE USER thinkhazard;

CREATE DATABASE thinkhazard OWNER thinkhazard;
\connect thinkhazard;
CREATE EXTENSION postgis;
CREATE EXTENSION unaccent;

CREATE DATABASE thinkhazard_admin OWNER thinkhazard;
\connect thinkhazard_admin;
CREATE EXTENSION postgis;
CREATE EXTENSION unaccent;

CREATE DATABASE thinkhazard_test OWNER thinkhazard;
\connect thinkhazard_test;
CREATE EXTENSION postgis;
CREATE EXTENSION unaccent;
