#!/bin/bash

# Ensure Django migrations are applied
echo "Checking database status..."

# Try to run migrations - this will create tables if they don't exist
python manage.py migrate --noinput

# Check if specific triage tables exist
python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name LIKE \"triage%\";')
        tables = cursor.fetchall()
        print(f'Triage tables found: {[t[0] for t in tables]}')
except Exception as e:
    print(f'Error checking tables: {e}')
"

echo "Migration check completed!"
