##########################################
# Common base for build/test and runtime #
##########################################

FROM python:3.8-slim-buster as base

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install middleware
RUN apt-get update && apt-get install -y \
    # Install postgis for shp2pgsql as ogr2ogr from distrib is not compatible with PostgreSQL 12
    postgis \
    git python-numpy gdal-bin libgdal-dev tidy gnupg2 unzip \
    # pyppeteer dependencies (cf https://github.com/puppeteer/puppeteer/issues/1345)
    gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && echo "deb http://apt.postgresql.org/pub/repos/apt/ buster-pgdg main" >  /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y postgresql-client-12 \
    && rm -rf /var/lib/apt/lists/*

ENV HOME=/home/user \
    NODE_PATH=/opt/thinkhazard/node_modules

RUN mkdir -p /home/user/.local/share/pyppeteer/ && chmod -R 777 /home/user

# install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && rm --recursive --force /tmp/* /var/tmp/* $HOME/.cache/* \
    && pyppeteer-install

# Administrative divisions cache
RUN mkdir /tmp/admindivs && chmod 777 /tmp/admindivs
VOLUME /tmp/admindivs

# Layer cache
RUN mkdir /tmp/hazardsets && chmod 777 /tmp/hazardsets
VOLUME /tmp/hazardsets

# Geonode API cache
RUN mkdir /tmp/geonode_api && chmod 777 /tmp/geonode_api
VOLUME /tmp/geonode_api

# PostgreSQL backups
RUN mkdir /tmp/backups && chmod 777 /tmp/backups
VOLUME /tmp/backups

ENV AWS_ENDPOINT_URL= \
    GEONODE_URL=tbd \
    GEONODE_USERNAME=tbd \
    GEONODE_API_KEY=tbd \
    INI_FILE=c2c://production.ini \
    LOG_LEVEL_ROOT=WARN \
    LOG_LEVEL_THINKHAZARD=WARN \
    LOG_LEVEL_SQLALCHEMY=WARN \
    USE_CACHE=FALSE \
    TX_BRANCH=test

########################
# Build and test image #
########################
FROM base as builder

RUN apt-get update && apt-get install -y \
    gettext \
    make \
    curl

RUN \
  . /etc/os-release && \
  echo "deb https://deb.nodesource.com/node_12.x ${VERSION_CODENAME} main" > /etc/apt/sources.list.d/nodesource.list && \
  curl --silent https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - && \
  apt-get update && \
  apt-get install --assume-yes --no-install-recommends \
    'nodejs=12.*' \
    && \
  echo "Keep apt cache for now"
  #apt-get clean && \
  #rm --recursive --force /var/lib/apt/lists/*

COPY package.json /opt/thinkhazard/
RUN cd /opt/thinkhazard/ && npm install
ENV PATH=${PATH}:${NODE_PATH}/.bin/

COPY ./requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt \
    && rm --recursive --force /tmp/pip* /var/tmp/* $HOME/.cache/*

WORKDIR /app
COPY . /app/

ARG TX_USR
ARG TX_PWD
RUN TX_USR=$TX_USR \
    TX_PWD=$TX_PWD \
    make -f docker.mk build

RUN pip install --no-deps -e .

RUN chmod 777 /app
USER www-data
CMD ["sh", "-c", "pserve ${INI_FILE} -n main"]

#################
# Runtime image #
#################
FROM base as app

COPY --from=builder /opt/thinkhazard/ /opt/thinkhazard/

WORKDIR /app
COPY --from=builder /app/ /app/
RUN pip install --no-deps -e .

USER www-data
CMD ["sh", "-c", "pserve ${INI_FILE} -n main"]
