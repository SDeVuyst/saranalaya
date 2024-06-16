# syntax=docker/dockerfile:1
FROM python:3

RUN apt-get update && apt-get install -y postgresql-client-16 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . code
WORKDIR /code

EXPOSE 8100
