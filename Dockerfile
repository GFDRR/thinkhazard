FROM python:3.8-slim

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install middleware
RUN apt-get update && apt-get install -y \
python-numpy gdal-bin libgdal-dev tidy \
&& rm -rf /var/lib/apt/lists/*

# install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY ./dev-requirements.txt /app/dev-requirements.txt
RUN pip install -r dev-requirements.txt

# copy project
COPY . /app/
RUN pip install -e .
