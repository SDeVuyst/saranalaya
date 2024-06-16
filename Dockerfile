# syntax=docker/dockerfile:1
FROM python:3

# Install build dependencies
RUN apt-get update \
    && apt-get install -y build-essential wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install PostgreSQL client from source
RUN wget https://ftp.postgresql.org/pub/source/v16.0/postgresql-16.0.tar.gz\
    && tar -xvzf postgresql-16.0.tar.gz \
    && cd postgresql-16.0 \
    && ./configure --without-icu --without-readline --without-zlib\
    && make \
    && make install \
    && cd .. \
    && rm -rf postgresql-16.0 postgresql-16.0.tar.gz

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . code
WORKDIR /code

EXPOSE 8100

RUN apt-get -y update && apt-get -y upgrade
