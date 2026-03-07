from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.management import call_command
from django.db import connection


@csrf_exempt
@require_http_methods(["POST"])
def force_migrations(request):
    """Force run migrations via API call"""
    try:
        # Create all required triage tables manually
        with connection.cursor() as cursor:
            # Create triage_villagecoordinates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS triage_villagecoordinates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    village VARCHAR(100) NOT NULL,
                    district VARCHAR(100) NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    lookup_count INTEGER DEFAULT 1
                )
            """)
            
            # Create index if it doesn't exist
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS triage_vill_village_79ec71_idx 
                ON triage_villagecoordinates(village, district)
            """)
            
            # Create triage_triagecase table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS triage_triagecase (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_token VARCHAR(50) UNIQUE NOT NULL,
                    age_group VARCHAR(50) NOT NULL,
                    sex VARCHAR(10) NOT NULL,
                    district VARCHAR(100) NOT NULL,
                    village VARCHAR(100),
                    complaint_group VARCHAR(100),
                    patient_relation VARCHAR(50),
                    consent_medical_triage BOOLEAN NOT NULL,
                    consent_data_sharing BOOLEAN NOT NULL,
                    consent_follow_up BOOLEAN NOT NULL,
                    location_consent BOOLEAN DEFAULT FALSE,
                    complaint_text TEXT,
                    device_location_lat REAL,
                    device_location_lng REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create triage_triagesession table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS triage_triagesession (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_token VARCHAR(50) NOT NULL,
                    session_data TEXT,
                    current_step INTEGER DEFAULT 1,
                    is_completed BOOLEAN DEFAULT FALSE,
                    created_by_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add missing columns if table already exists
            try:
                cursor.execute("ALTER TABLE triage_triagesession ADD COLUMN created_by_id INTEGER")
            except:
                pass  # Column might already exist
            try:
                cursor.execute("ALTER TABLE triage_triagesession ADD COLUMN updated_by_id INTEGER")
            except:
                pass  # Column might already exist
            
        return JsonResponse({
            'status': 'success',
            'message': 'All triage tables created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
