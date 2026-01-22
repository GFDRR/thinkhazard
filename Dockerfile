##########################################
# Common base for build/test and runtime #
##########################################

FROM python:3.14-slim-bookworm AS base

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install middleware
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update && apt-get install -y \
    # Install postgis for shp2pgsql as ogr2ogr from distrib is not compatible with PostgreSQL 12
    postgis \
    curl git python3-numpy gdal-bin libgdal-dev tidy gnupg2 unzip \
    && apt install -y postgresql-common gnupg \
    && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
    && apt-get update && apt-get install -y postgresql-client-17

RUN curl -L -o /tmp/tx-linux-amd64.tar.gz https://github.com/transifex/cli/releases/download/v1.6.7/tx-linux-amd64.tar.gz \
    && tar -C /usr/local/bin -xf /tmp/tx-linux-amd64.tar.gz tx \
    && chmod +x /usr/local/bin/tx \
    && rm -f /tmp/tx-linux-amd64.tar.gz

ENV HOME=/home/user \
    NODE_PATH=/opt/thinkhazard/node_modules

# install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache \
    pip install -r /app/requirements.txt

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

RUN mkdir -p /home/user && chmod 777 /home/user

ENV AWS_ENDPOINT_URL= \
    GEONODE_URL=tbd \
    GEONODE_USERNAME=tbd \
    GEONODE_API_KEY=tbd \
    INI_FILE=c2c://production.ini \
    LOG_LEVEL_ROOT=WARN \
    LOG_LEVEL_THINKHAZARD=WARN \
    LOG_LEVEL_SQLALCHEMY=WARN \
    USE_CACHE=FALSE


########################
# Build frontend files #
########################
FROM node:18-alpine AS node

WORKDIR /app/thinkhazard/
COPY package.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install

COPY thinkhazard/static/ ./thinkhazard/static/

RUN mkdir -p thinkhazard/static/build && \
    npx lessc --include-path=node_modules --clean-css thinkhazard/static/less/index.less thinkhazard/static/build/index.min.css && \
    npx lessc --include-path=node_modules thinkhazard/static/less/index.less thinkhazard/static/build/index.css && \
    npx lessc --include-path=node_modules --clean-css thinkhazard/static/less/report.less thinkhazard/static/build/report.min.css && \
    npx lessc --include-path=node_modules thinkhazard/static/less/report.less thinkhazard/static/build/report.css && \
    npx lessc --include-path=node_modules --clean-css thinkhazard/static/less/report_print.less thinkhazard/static/build/report_print.min.css && \
    npx lessc --include-path=node_modules thinkhazard/static/less/report_print.less thinkhazard/static/build/report_print.css && \
    npx lessc --include-path=node_modules --clean-css thinkhazard/static/less/common.less thinkhazard/static/build/common.min.css && \
    npx lessc --include-path=node_modules thinkhazard/static/less/common.less thinkhazard/static/build/common.css && \
    npx lessc --include-path=node_modules --clean-css thinkhazard/static/less/admin.less thinkhazard/static/build/admin.min.css && \
    npx lessc --include-path=node_modules thinkhazard/static/less/admin.less thinkhazard/static/build/admin.css

RUN mkdir -p thinkhazard/static/fonts && \
    cp node_modules/font-awesome/fonts/fontawesome-webfont.* thinkhazard/static/fonts/

RUN npx jshint thinkhazard/static/js/**/*.js


########################
# Build and test image #
########################
FROM base AS builder

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update && apt-get install -y \
    gettext \
    make \
    curl

COPY --from=node /app/thinkhazard/node_modules /opt/thinkhazard/node_modules
COPY --from=node /app/thinkhazard/thinkhazard/static/build /opt/thinkhazard/thinkhazard/static/build

# Install OpenLayers from release, not source.
RUN mkdir --parent /opt/thinkhazard/node_modules/openlayers/dist \
    && cd /opt/thinkhazard/node_modules/openlayers/dist \
    && curl -J -L -o v4.5.0-dist.zip \
        "https://github.com/openlayers/openlayers/releases/download/v4.5.0/v4.5.0-dist.zip" \
    && unzip v4.5.0-dist.zip && rm -f v4.5.0-dist.zip \
    && mv v4.5.0-dist/* . && rm -rf v4.5.0-dist

COPY ./requirements-dev.txt /app/requirements-dev.txt
RUN --mount=type=cache,target=/root/.cache \
    pip install -r /app/requirements-dev.txt

WORKDIR /app
COPY . /app/

ARG TX_TOKEN
ARG TX_BRANCH
RUN TX_TOKEN=$TX_TOKEN TX_BRANCH=$TX_BRANCH \
    && make -f docker.mk build

RUN pip install --no-deps -e .

RUN chmod 777 /app

ARG TX_BRANCH
ENV TX_BRANCH=$TX_BRANCH

USER www-data
CMD ["sh", "-c", "pserve ${INI_FILE} -n main"]

#################
# Runtime image #
#################
FROM base AS app

COPY --from=builder /opt/thinkhazard/ /opt/thinkhazard/

WORKDIR /app
COPY --from=builder /app/ /app/
RUN pip install --no-deps -e .

ARG TX_BRANCH
ENV TX_BRANCH=$TX_BRANCH

USER www-data
CMD ["sh", "-c", "pserve ${INI_FILE} -n main"]
