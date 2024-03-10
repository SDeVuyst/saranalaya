# syntax=docker/dockerfile:1
FROM python:3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV AMOUNT_ADOPTION_PARENTS=186

WORKDIR /.
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get -y update && apt-get -y upgrade
