#!/bin/sh

set -e

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate --noinput

# Run the actual application server (adjust if using something else)
exec "$@"
