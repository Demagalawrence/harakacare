#!/usr/bin/env python
"""
Production Setup Script for HarakaCare
Creates facilities and users for production deployment
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'harakacare.settings')
django.setup()

from django.contrib.auth.models import User
from apps.facilities.models import Facility
from apps.core.models import UserProfile

def create_production_facilities():
    """Create facilities for production"""
    
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
    
    created_facilities = []
    for facility_data in facilities_data:
        facility, created = Facility.objects.get_or_create(
            name=facility_data['name'],
            defaults=facility_data
        )
        created_facilities.append(facility)
        print(f"✅ {'Created' if created else 'Found'} facility: {facility.name}")
    
    return created_facilities

def create_production_users():
    """Create users for production"""
    
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
        # Create or get user
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
            print(f"✅ Created user: {user.username}")
        else:
            print(f"📋 User already exists: {user.username}")
        
        # Create user profile
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
            print(f"✅ Created profile for: {user.username}")
        else:
            print(f"📋 Profile already exists for: {user.username}")
        
        print(f"   🏥 Facility: {facility.name}")
        print(f"   👤 Role: {user_data['role']}")
        print()

def create_admin_user():
    """Create admin user"""
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@harakacare.ug',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ Created admin user: admin/admin123")
    else:
        print("📋 Admin user already exists: admin")

def main():
    """Main setup function"""
    print("🚀 Setting up HarakaCare Production Environment")
    print("=" * 50)
    
    # Create facilities
    print("\n🏥 Creating Facilities...")
    facilities = create_production_facilities()
    
    # Create users
    print("\n👤 Creating Users...")
    create_production_users()
    
    # Create admin
    print("\n🔐 Creating Admin User...")
    create_admin_user()
    
    print("\n✅ Production Setup Complete!")
    print("\n🔑 Login Credentials:")
    print("   Kampala Referral Hospital: kampala_staff / kampala123")
    print("   Mulago National Hospital: mulago_staff / mulago123")
    print("   Luwero General Hospital: luwero_staff / luwero123")
    print("   System Admin: admin / admin123")

if __name__ == '__main__':
    main()
