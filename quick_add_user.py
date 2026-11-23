#!/usr/bin/env python
"""
Quick script to add a user to a hospital facility
Usage: python quick_add_user.py
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'harakacare.settings.base')
django.setup()

from django.contrib.auth import get_user_model
from apps.core.models import UserProfile
from apps.facilities.models import Facility

User = get_user_model()

def add_user_to_facility():
    """Interactive script to add user to facility"""
    
    print("🏥 Add User to Hospital Facility")
    print("=" * 40)
    
    # Show available facilities
    facilities = Facility.objects.all()
    if not facilities:
        print("[ERROR] No facilities found. Please create facilities first.")
        return
    
    print("\n[CLIPBOARD] Available Facilities:")
    for i, facility in enumerate(facilities, 1):
        print(f"   {i}. {facility.name} ({facility.facility_type})")
    
    # Get facility choice
    try:
        facility_choice = int(input("\n🏥 Select facility (number): ")) - 1
        if facility_choice < 0 or facility_choice >= len(facilities):
            print("[ERROR] Invalid facility choice")
            return
        facility = facilities[facility_choice]
    except ValueError:
        print("[ERROR] Please enter a valid number")
        return
    
    # Get user details
    username = input("[USER] Username: ").strip()
    if not username:
        print("[ERROR] Username is required")
        return
    
    email = input("[EMAIL] Email: ").strip()
    first_name = input("[MEMO] First name: ").strip()
    last_name = input("[MEMO] Last name: ").strip()
    password = input("[LOCK] Password: ").strip()
    
    if not password:
        password = "password123"  # Default password
        print(f"WARNING:  Using default password: {password}")
    
    # Get role
    roles = UserProfile.UserRole.choices
    print("\n👥 Available Roles:")
    for i, (role, display) in enumerate(roles, 1):
        print(f"   {i}. {display}")
    
    try:
        role_choice = int(input("👥 Select role (number): ")) - 1
        if role_choice < 0 or role_choice >= len(roles):
            print("[ERROR] Invalid role choice")
            return
        role = roles[role_choice][0]
    except ValueError:
        print("[ERROR] Please enter a valid number")
        return
    
    department = input("🏢 Department (optional): ").strip()
    phone = input("[CAMERA] Phone (optional): ").strip()
    license_num = input("[CLIPBOARD] License number (optional): ").strip()
    
    # Create user
    try:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_staff': True  # Give admin access
            }
        )
        
        if created:
            user.set_password(password)
            user.save()
            print(f"[OK] Created user: {user.get_full_name()}")
        else:
            print(f"[MEMO] User already exists: {user.get_full_name()}")
        
        # Create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'facility': facility,
                'role': role,
                'department': department or None,
                'phone_number': phone or None,
                'license_number': license_num or None,
                'is_active_staff': True,
                'can_view_all_facilities': False
            }
        )
        
        if created:
            print(f"[OK] Created profile and assigned to {facility.name}")
        else:
            profile.facility = facility
            profile.role = role
            profile.department = department or None
            profile.phone_number = phone or None
            profile.license_number = license_num or None
            profile.save()
            print(f"[OK] Updated profile and assigned to {facility.name}")
        
        print(f"\n🎉 Success! User can now login and access {facility.name}")
        print(f"[LOCK] Login: {username} / {password}")
        print(f"🌐 Admin URL: http://127.0.0.1:8000/harakacare-admin/")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")

if __name__ == '__main__':
    add_user_to_facility()
