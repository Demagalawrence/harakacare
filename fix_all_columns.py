#!/usr/bin/env python
import os
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'harakacare.settings.production')
django.setup()

# List of all possible missing columns
missing_columns = [
    'patient_phone',
    'patient_phone_number', 
    'geocoding_display_name',
    'geocoding_accuracy',
    'geocoding_confidence',
    'geocoding_method',
    'geocoding_source',
    'location_accuracy',
    'location_method',
    'location_timestamp',
    'geocoding_raw_response',
    'geocoding_processed_at',
    'geocoding_provider',
    'geocoding_version',
    'geocoding_cache_hit',
    'geocoding_query',
    'geocoding_admin_level',
    'geocoding_postal_code',
    'geocoding_country',
    'geocoding_country_code',
    'geocoding_state',
    'geocoding_county',
    'geocoding_city',
    'geocoding_suburb',
    'geocoding_neighbourhood',
    'geocoding_road',
    'geocoding_house_number',
    'geocoding_latitude',
    'geocoding_longitude'
]

print("🔧 Adding all missing columns to triage_triagesession...")

for column in missing_columns:
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE triage_triagesession ADD COLUMN {column} TEXT")
            print(f"✅ Added {column}")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print(f"✅ {column} already exists")
        else:
            print(f"❌ Error adding {column}: {e}")

print("\n📋 Checking final table structure...")
try:
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(triage_triagesession)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Total columns: {len(columns)}")
        print(f"📋 Columns: {sorted(columns)}")
except Exception as e:
    print(f"❌ Error checking table: {e}")

print("\n🎉 Column fixing complete!")
