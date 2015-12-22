#! /bin/bash

# This script is a helper to generate new schema for the database
# It:
# - Drops the database and recreates it
# - Creates the tables given the model (initialize)
# - Populates the database with enum tables
# - Populates the database with administrative divisions
# - Creates an image file representing the DB model
#
# This can be useful while working on the python model to make sure that it
# looks like it really should in postgreSQL
#
# This script is intentionaly not exposed as target in the makefile.

if [[ $# -eq 0 ]] ; then
    echo 'You must provide the name of the database'
    echo 'The same as provided in local.ini'
    exit 0
fi

echo "Restarting PostgreSQL"
sudo /etc/init.d/postgresql restart
echo "Drop existing database"
sudo -u postgres dropdb $1
sudo -u postgres createuser www-data --no-superuser --no-createdb --no-createrole -U postgres
echo "Create new database"
sudo -u postgres createdb -O www-data $1
echo "Postgis and schema"
sudo -u postgres psql -d $1 -c 'CREATE EXTENSION postgis;'
echo "Initialize"
.build/venv/bin/initialize_thinkhazard_db development.ini

echo "Creating database diagram"
cd /tmp
sudo -u postgres postgresql_autodoc -d $1
dot -Tpng $1.dot > $1.png
cd -

# FIXME put the files in project release
# See https://help.github.com/articles/distributing-large-binaries/

echo "Creating administrative divisions - level 0"
echo "Download admin divs shapefiles"
wget -nc "http://dev.camptocamp.com/files/thinkhazard/g2015_2014_0.zip"
echo "Unzipping"
unzip -o g2015_2014_0.zip
echo "Import into database"
shp2pgsql -s 4326 -W LATIN1 g2015_2014_0/g2015_2014_0.shp | sudo -u postgres psql -d $1
echo "Cleaning up"
rm -rf g2015_2014*
echo "Removing duplicates"
sudo -u postgres psql -d $1 -c "DELETE FROM g2015_2014_0 WHERE gid = 177;"
echo "Populate admin divs table"
sudo -u postgres psql -d $1 -c "
INSERT INTO datamart.administrativedivision (code, leveltype_id, name, parent_code, geom)
SELECT adm0_code, 1, adm0_name, NULL, ST_Transform(geom, 3857) as geom
FROM g2015_2014_0;
SELECT DropGeometryColumn('public', 'g2015_2014_0', 'geom');
DROP TABLE g2015_2014_0;
"

echo "Creating administrative divisions - level 1"
echo "Download admin divs shapefiles"
wget -nc "http://dev.camptocamp.com/files/thinkhazard/g2015_2014_1.zip"
echo "Unzipping"
unzip -o g2015_2014_1.zip
echo "Import into database"
shp2pgsql -s 4326 -W LATIN1 g2015_2014_1/g2015_2014_1.shp | sudo -u postgres psql -d $1
echo "Cleaning up"
rm -rf g2015_2014*
echo "Populate admin divs table"
sudo -u postgres psql -d $1 -c "
INSERT INTO datamart.administrativedivision (code, leveltype_id, name, parent_code, geom)
SELECT adm1_code, 2, adm1_name, adm0_code, ST_Transform(geom, 3857) as geom
FROM g2015_2014_1;
SELECT DropGeometryColumn('public', 'g2015_2014_1', 'geom');
DROP TABLE g2015_2014_1;
"

echo "Creating administrative divisions - level 2"
echo "Download admin divs shapefiles"
wget -nc "http://dev.camptocamp.com/files/thinkhazard/g2015_2014_2.zip"
echo "Unzipping"
unzip -o g2015_2014_2.zip
echo "Import into database"
shp2pgsql -s 4326 -W LATIN1 g2015_2014_2/g2015_2014_2.shp | sudo -u postgres psql -d $1
echo "Cleaning up"
rm -rf g2015_2014*
echo "Removing duplicates"
sudo -u postgres psql -d $1 -c "DELETE FROM g2015_2014_2 WHERE gid = 5340;"
sudo -u postgres psql -d $1 -c "DELETE FROM g2015_2014_2 WHERE gid = 5382;"
sudo -u postgres psql -d $1 -c "DELETE FROM g2015_2014_2 WHERE gid = 5719;"
sudo -u postgres psql -d $1 -c "DELETE FROM g2015_2014_2 WHERE gid = 20775;"
sudo -u postgres psql -d $1 -c "DELETE FROM g2015_2014_2 WHERE gid = 1059;"
echo "Populate admin divs table"
sudo -u postgres psql -d $1 -c "
INSERT INTO datamart.administrativedivision (code, leveltype_id, name, parent_code, geom)
SELECT adm2_code, 3, adm2_name, adm1_code, ST_Transform(geom, 3857) as geom
FROM g2015_2014_2;
SELECT DropGeometryColumn('public', 'g2015_2014_2', 'geom');
DROP TABLE g2015_2014_2;
"
