from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.facilities.models import Facility
from apps.core.models import UserProfile


class Command(BaseCommand):
    help = 'Create production facilities and users automatically'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Setting up HarakaCare Production Environment...')
        
        # Create facilities
        facilities_data = [
            {
                'name': 'Kampala Referral Hospital',
                'facility_type': 'referral_hospital',
                'address': 'Kampala, Uganda (Serves: Kampala, Wakiso, Mpigi)',
                'district': 'Kampala',
                'phone_number': '+256414123456',
                'total_beds': 500,
                'available_beds': 150,
                'staff_count': 200,
                'ambulance_available': True,
                'services_offered': ['emergency', 'general_medicine', 'surgery', 'obstetrics', 'maternal_health'],
            },
            {
                'name': 'Mulago National Hospital',
                'facility_type': 'national_referral',
                'address': 'Mulago, Kampala (Serves: Kampala, Mukono, Buikwe)',
                'district': 'Kampala',
                'phone_number': '+256414789012',
                'total_beds': 800,
                'available_beds': 200,
                'staff_count': 350,
                'ambulance_available': True,
                'services_offered': ['emergency', 'general_medicine', 'surgery', 'pediatrics', 'obstetrics'],
            },
            {
                'name': 'Luwero General Hospital',
                'facility_type': 'general_hospital',
                'address': 'Luwero Town (Serves: Luwero, Nakasongola, Kayunga)',
                'district': 'Luwero',
                'phone_number': '+256414555666',
                'total_beds': 100,
                'available_beds': 50,
                'staff_count': 75,
                'ambulance_available': True,
                'services_offered': ['emergency', 'general_medicine', 'obstetrics', 'maternal_health'],
            }
        ]
        
        for facility_data in facilities_data:
            facility, created = Facility.objects.get_or_create(
                name=facility_data['name'],
                defaults=facility_data
            )
            status = '✅ Created' if created else '📋 Found'
            self.stdout.write(f'{status} facility: {facility.name}')
        
        # Create users
        users_data = [
            {
                'username': 'kampala_staff',
                'password': 'kampala123',
                'email': 'staff@kampalareferral.ug',
                'first_name': 'John',
                'last_name': 'Ochieng',
                'facility_name': 'Kampala Referral Hospital',
                'role': 'medical_officer',
                'department': 'Emergency',
            },
            {
                'username': 'mulago_staff',
                'password': 'mulago123',
                'email': 'staff@mulago.go.ug',
                'first_name': 'Sarah',
                'last_name': 'Nakato',
                'facility_name': 'Mulago National Hospital',
                'role': 'nurse',
                'department': 'Emergency',
            },
            {
                'username': 'luwero_staff',
                'password': 'luwero123',
                'email': 'staff@luwerohospital.ug',
                'first_name': 'Grace',
                'last_name': 'Nakintu',
                'facility_name': 'Luwero General Hospital',
                'role': 'nurse_midwife',
                'department': 'Maternity',
            }
        ]
        
        for user_data in users_data:
            user, user_created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_staff': True,
                }
            )
            
            if user_created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'✅ Created user: {user.username}')
            else:
                self.stdout.write(f'📋 User exists: {user.username}')
            
            # Create profile
            facility = Facility.objects.get(name=user_data['facility_name'])
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'facility': facility,
                    'role': user_data['role'],
                    'department': user_data['department'],
                    'phone_number': '+256700000000',
                    'is_active_staff': True,
                    'can_view_all_facilities': False,
                }
            )
            
            if profile_created:
                self.stdout.write(f'✅ Created profile for: {user.username}')
        
        # Create admin
        admin_user, admin_created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@harakacare.ug',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if admin_created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write('✅ Created admin user: admin/admin123')
        else:
            self.stdout.write('📋 Admin user exists: admin')
        
        self.stdout.write('\n✅ Production Setup Complete!')
        self.stdout.write('\n🔑 Login Credentials:')
        self.stdout.write('   Kampala Referral Hospital: kampala_staff / kampala123')
        self.stdout.write('   Mulago National Hospital: mulago_staff / mulago123')
        self.stdout.write('   Luwero General Hospital: luwero_staff / luwero123')
        self.stdout.write('   System Admin: admin / admin123')
