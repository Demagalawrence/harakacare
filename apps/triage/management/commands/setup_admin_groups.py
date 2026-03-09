"""
Django management command to set up HarakaCare admin groups and permissions
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from apps.triage.models import TriageSession, TriageDecision, Conversation


class Command(BaseCommand):
    help = 'Create HarakaCare admin groups with appropriate permissions'

    def handle(self, *args, **options):
        self.stdout.write('Setting up HarakaCare admin groups and permissions...')

        # Create groups
        facility_staff, created = Group.objects.get_or_create(name='Facility Staff')
        if created:
            self.stdout.write(self.style.SUCCESS('Created "Facility Staff" group'))

        harakacare_admin_group, created = Group.objects.get_or_create(name='HarakaCare Admin')
        if created:
            self.stdout.write(self.style.SUCCESS('Created "HarakaCare Admin" group'))

        # Get content types
        triage_session_ct = ContentType.objects.get_for_model(TriageSession)
        triage_decision_ct = ContentType.objects.get_for_model(TriageDecision)
        conversation_ct = ContentType.objects.get_for_model(Conversation)

        # Facility Staff permissions (read-only for their district)
        facility_permissions = [
            # Can view triage sessions
            Permission.objects.get_or_create(
                codename='view_triagesession',
                content_type=triage_session_ct,
                defaults={'name': 'Can view triage session'}
            )[0],
            # Can view triage decisions
            Permission.objects.get_or_create(
                codename='view_tridgedecision',
                content_type=triage_decision_ct,
                defaults={'name': 'Can view triage decision'}
            )[0],
        ]

        facility_staff.permissions.set(facility_permissions)
        self.stdout.write(self.style.SUCCESS('Set up Facility Staff permissions'))

        # HarakaCare Admin permissions (full access)
        admin_permissions = []
        for content_type in [triage_session_ct, triage_decision_ct, conversation_ct]:
            # Add all permissions for these models
            admin_permissions.extend(
                Permission.objects.filter(content_type=content_type)
            )

        harakacare_admin_group.permissions.set(admin_permissions)
        self.stdout.write(self.style.SUCCESS('Set up HarakaCare Admin permissions'))

        # Create default admin user if none exists
        if not User.objects.filter(is_superuser=True).exists():
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@harakacare.ug',
                password='admin123',  # Change this in production!
                is_staff=True,
                is_superuser=True
            )
            admin_user.groups.add(harakacare_admin_group)
            self.stdout.write(self.style.SUCCESS('Created default admin user: admin/admin123'))

        # Create sample facility staff user
        facility_user, created = User.objects.get_or_create(
            username='facility_staff',
            defaults={
                'email': 'staff@harakacare.ug',
                'is_staff': True,
            }
        )
        if created:
            facility_user.set_password('staff123')
            facility_user.save()
            facility_user.groups.add(facility_staff)
            self.stdout.write(self.style.SUCCESS('Created sample facility staff user: facility_staff/staff123'))

        self.stdout.write(self.style.SUCCESS('✅ HarakaCare admin setup complete!'))
        self.stdout.write('\nAccess URLs:')
        self.stdout.write('  Default Django Admin: /admin/')
        self.stdout.write('  HarakaCare Clinical Dashboard: /harakacare-admin/')
        self.stdout.write('\nDefault Users:')
        self.stdout.write('  Admin: admin/admin123 (full access)')
        self.stdout.write('  Facility Staff: facility_staff/staff123 (limited access)')
