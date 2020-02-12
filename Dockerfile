##########################################
# Common base for build/test and runtime #
##########################################

FROM python:3.8-slim as base

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install middleware
RUN apt-get update && apt-get install -y \
    python-numpy gdal-bin libgdal-dev tidy gnupg \
    # pyppeteer dependencies (cf https://github.com/puppeteer/puppeteer/issues/1345)
    gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget \
    && rm -rf /var/lib/apt/lists/*

# install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt && pyppeteer-install


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

WORKDIR /app

COPY package.json /app/
RUN cd /app/ && npm install

COPY ./requirements-dev.txt /app/requirements-dev.txt
RUN pip install -r requirements-dev.txt

COPY . /app/

ARG TX_USR
ARG TX_PWD
RUN TX_USR=$TX_USR TX_PWD=$TX_PWD make -f docker.mk build

RUN pip install --no-deps -e .

#################
# Runtime image #
#################
FROM base as app

WORKDIR /app
COPY --from=builder /app/ /app/
RUN pip install --no-deps -e .
