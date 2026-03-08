from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.management import call_command
from django.db import connection


@csrf_exempt
@require_http_methods(["GET", "POST"])
def force_migrations(request):
    """Force run migrations via API call - automatically called to ensure tables exist"""
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
            
            # Check if triage_triagesession has all required columns, if not recreate it
            cursor.execute("PRAGMA table_info(triage_triagesession)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            required_columns = ['patient_token', 'status', 'session_status', 'complaint_group', 'age_group', 'sex', 'risk_level', 'risk_confidence']
            
            # If key columns are missing, recreate the table
            if not all(col in existing_columns for col in required_columns):
                cursor.execute("DROP TABLE IF EXISTS triage_triagesession")
                cursor.execute("""
                    CREATE TABLE triage_triagesession (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_token VARCHAR(50) NOT NULL,
                        session_data TEXT,
                        current_step INTEGER DEFAULT 1,
                        is_completed BOOLEAN DEFAULT FALSE,
                        is_active BOOLEAN DEFAULT TRUE,
                        status VARCHAR(50) DEFAULT 'active',
                        status_changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status_reason TEXT,
                        created_by_id INTEGER,
                        updated_by_id INTEGER,
                        patient_phone TEXT,
                        patient_phone_number TEXT,
                        geocoding_display_name TEXT,
                        geocoding_accuracy REAL,
                        geocoding_confidence REAL,
                        geocoding_method TEXT,
                        geocoding_source TEXT,
                        location_accuracy REAL,
                        location_method TEXT,
                        location_timestamp DATETIME,
                        geocoding_raw_response TEXT,
                        geocoding_processed_at DATETIME,
                        geocoding_provider TEXT,
                        geocoding_version TEXT,
                        geocoding_cache_hit BOOLEAN DEFAULT FALSE,
                        geocoding_query TEXT,
                        geocoding_admin_level TEXT,
                        geocoding_postal_code TEXT,
                        geocoding_country TEXT,
                        geocoding_country_code TEXT,
                        geocoding_state TEXT,
                        geocoding_county TEXT,
                        geocoding_city TEXT,
                        geocoding_suburb TEXT,
                        geocoding_neighbourhood TEXT,
                        geocoding_road TEXT,
                        geocoding_house_number TEXT,
                        geocoding_latitude REAL,
                        geocoding_longitude REAL,
                        session_status VARCHAR(50) DEFAULT 'active',
                        complaint_text TEXT,
                        complaint_group VARCHAR(100),
                        age_group VARCHAR(50),
                        sex VARCHAR(10),
                        patient_relation VARCHAR(50),
                        symptom_indicators TEXT,
                        symptom_severity TEXT,
                        symptom_duration TEXT,
                        progression_status TEXT,
                        red_flag_indicators TEXT,
                        has_red_flags BOOLEAN DEFAULT FALSE,
                        red_flag_detected_at_turn INTEGER,
                        risk_modifiers TEXT,
                        pregnancy_status TEXT,
                        has_chronic_conditions BOOLEAN DEFAULT FALSE,
                        on_medication BOOLEAN DEFAULT FALSE,
                        district VARCHAR(100),
                        subcounty VARCHAR(100),
                        village VARCHAR(100),
                        device_location_lat REAL,
                        device_location_lng REAL,
                        location_consent BOOLEAN DEFAULT FALSE,
                        primary_symptom VARCHAR(100),
                        secondary_symptoms TEXT,
                        red_flags TEXT,
                        chronic_conditions TEXT,
                        additional_description TEXT,
                        consent_medical_triage BOOLEAN DEFAULT FALSE,
                        consent_data_sharing BOOLEAN DEFAULT FALSE,
                        consent_follow_up BOOLEAN DEFAULT FALSE,
                        risk_level VARCHAR(50),
                        risk_confidence REAL,
                        follow_up_priority VARCHAR(50),
                        ai_model_version VARCHAR(50),
                        assessment_completed_at DATETIME,
                        forwarded_to_followup BOOLEAN DEFAULT FALSE,
                        forwarded_to_facility BOOLEAN DEFAULT FALSE,
                        channel VARCHAR(50),
                        conversation_turns INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
        return JsonResponse({
            'status': 'success',
            'message': 'All triage tables verified/created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
