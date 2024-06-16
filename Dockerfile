# syntax=docker/dockerfile:1
FROM python:3

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Add PostgreSQL APT repository to install PostgreSQL 16 client tools
RUN apt-get update && \
    apt-get install -y wget gnupg2 lsb-release && \
    wget -qO - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-16

COPY . code
WORKDIR /code

EXPOSE 8100

RUN apt-get -y update && apt-get -y upgrade
