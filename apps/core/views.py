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
        # Create the triage_villagecoordinates table manually
        with connection.cursor() as cursor:
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
            
        return JsonResponse({
            'status': 'success',
            'message': 'triage_villagecoordinates table created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
