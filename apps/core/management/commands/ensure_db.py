from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Ensure all required database tables exist'

    def handle(self, *args, **options):
        self.stdout.write('Checking database tables...')
        
        # List of expected tables
        expected_tables = [
            'triage_triagecase',
            'triage_villagecoordinates',
            'facilities_facility',
            'patients_patient',
            'auth_user',
            'django_migrations',
        ]
        
        existing_tables = []
        missing_tables = []
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """)
            all_tables = [row[0] for row in cursor.fetchall()]
            
            for table in expected_tables:
                if table in all_tables:
                    existing_tables.append(table)
                else:
                    missing_tables.append(table)
        
        self.stdout.write(f'Existing tables: {existing_tables}')
        
        if missing_tables:
            self.stdout.write(self.style.ERROR(f'Missing tables: {missing_tables}'))
            self.stdout.write('Running migrations to create missing tables...')
            
            # Import and run migrations
            from django.core.management import call_command
            try:
                call_command('migrate', verbosity=2)
                self.stdout.write(self.style.SUCCESS('Migrations completed successfully!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Migration failed: {e}'))
        else:
            self.stdout.write(self.style.SUCCESS('All required tables exist!'))
