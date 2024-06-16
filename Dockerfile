# syntax=docker/dockerfile:1
FROM python:3

# Update package lists and install necessary tools
RUN apt-get update \
    && apt-get install -y wget gnupg2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add PostgreSQL repository and key
RUN echo "deb http://apt.postgresql.org/pub/repos/apt focal-pgdg main" >> /etc/apt/sources.list.d/pgdg.list \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

# Install PostgreSQL 16 client tools
RUN apt-get update \
    && apt-get install -y postgresql-client-16

# Optionally, clean up
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . code
WORKDIR /code

EXPOSE 8100
