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

echo "Restarting PostgreSQL"
sudo /etc/init.d/postgresql restart
echo "Drop existing database"
sudo -u postgres dropdb thinkhazard -U postgres
echo "Create new database"
sudo -u postgres createdb thinkhazard -U postgres
echo "Postgis and schema"
sudo -u postgres psql -d thinkhazard -c 'CREATE EXTENSION postgis;'
sudo -u postgres psql -d thinkhazard -c 'CREATE SCHEMA datamart;'
sudo -u postgres psql -d thinkhazard -c 'GRANT ALL ON SCHEMA datamart TO "www-data";'
echo "Initialize"
.build/venv/bin/initialize_thinkhazard_db development.ini
.build/venv/bin/nosetests

echo "Creating database diagram"
cd /tmp
sudo -u postgres postgresql_autodoc -d thinkhazard
dot -Tpng thinkhazard.dot > thinkhazard.png
cd -
