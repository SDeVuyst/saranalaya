# syntax=docker/dockerfile:1
FROM python:3

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install PostgreSQL client tools
RUN apt-get update && apt-get install -y postgresql-client

COPY . code
WORKDIR /code

EXPOSE 8100

RUN apt-get -y update && apt-get -y upgrade
