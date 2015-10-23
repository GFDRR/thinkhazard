#! /bin/bash

# This script is a helper to generate new schema for the database
# It:
# - Drops the database and recreates it
# - Creates the tables given the model (initialize)
# - Populates the database with enum tables
# - Creates an image file representing the DB model
#
# This is useful while working on the python model to make sure that it looks
# like it really should in postgreSQL

echo "restart"
sudo /etc/init.d/postgresql restart
echo "drop"
sudo -u postgres dropdb thinkhazard -U postgres
echo "create"
sudo -u postgres createdb thinkhazard -U postgres
echo "postgis and schema"
sudo -u postgres psql -d thinkhazard -c 'CREATE EXTENSION postgis;'
sudo -u postgres psql -d thinkhazard -c 'CREATE SCHEMA datamart;'
sudo -u postgres psql -d thinkhazard -c 'GRANT ALL ON SCHEMA datamart TO "www-data";'
echo "initialize"
.build/venv/bin/initialize_thinkhazard_db development.ini

cd /tmp
sudo -u postgres postgresql_autodoc -d thinkhazard 
dot -Tpng thinkhazard.dot > thinkhazard.png
cd -
