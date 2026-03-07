from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Force migrate all apps and create missing tables'

    def handle(self, *args, **options):
        self.stdout.write('Force migrating all apps...')
        
        # Reset migration history for triage app only
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations WHERE app = 'triage'")
                self.stdout.write('Reset triage migration history')
        except Exception as e:
            self.stdout.write(f'Error resetting migration history: {e}')
        
        # Run migrations for all apps
        try:
            call_command('migrate', app_label='triage', verbosity=2)
            self.stdout.write(self.style.SUCCESS('Triage migrations completed!'))
            
            call_command('migrate', app_label='facilities', verbosity=2)
            self.stdout.write(self.style.SUCCESS('Facilities migrations completed!'))
            
            call_command('migrate', app_label='patients', verbosity=2)
            self.stdout.write(self.style.SUCCESS('Patients migrations completed!'))
            
            call_command('migrate', app_label='auth', verbosity=2)
            self.stdout.write(self.style.SUCCESS('Auth migrations completed!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {e}'))
        
        # Verify tables exist
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE '%triage%'
            """)
            triage_tables = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f'Triage tables: {triage_tables}')
            
            if 'triage_villagecoordinates' in triage_tables:
                self.stdout.write(self.style.SUCCESS('✅ triage_villagecoordinates table exists!'))
            else:
                self.stdout.write(self.style.ERROR('❌ triage_villagecoordinates table still missing!'))
                
                # Create it manually
                cursor.execute("""
                    CREATE TABLE triage_villagecoordinates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        village VARCHAR(100) NOT NULL,
                        district VARCHAR(100) NOT NULL,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        lookup_count INTEGER DEFAULT 1
                    )
                """)
                cursor.execute("""
                    CREATE UNIQUE INDEX triage_vill_village_79ec71_idx 
                    ON triage_villagecoordinates(village, district)
                """)
                self.stdout.write(self.style.SUCCESS('✅ Created triage_villagecoordinates table manually!'))
