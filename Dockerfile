# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

# 1. Install standard build tools and repository prerequisites
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg2 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Add the official PostgreSQL repository securely (without apt-key or lsb-release)
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(. /etc/os-release && echo "$VERSION_CODENAME")-pgdg main" > /etc/apt/sources.list.d/pgdg.list

# 3. Update and install postgresql-client-16
RUN apt-get update && apt-get install -y \
    postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose port
EXPOSE 8100

# Start the server
CMD ["gunicorn", "saranalaya.wsgi:application", "--bind", "0.0.0.0:8100"]