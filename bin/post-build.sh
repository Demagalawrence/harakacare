#!/bin/bash

# Run Django migrations after build
echo "Running Django migrations..."
python manage.py migrate --noinput

echo "Migrations completed successfully!"
