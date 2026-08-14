"""Guarantee a working super admin exists on a fresh Render database."""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create the default admin account if it is missing. "
        "Render uses an empty database; local users are not copied."
    )

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin").strip() or "admin"
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@company.com").strip() or "admin@company.com"
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "Admin@12345")
        reset_password = os.getenv("RESET_ADMIN_PASSWORD", "").lower() in ("true", "1", "yes")

        user = User.objects.filter(username__iexact=username).first()
        if user is None:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name="Super",
                last_name="Admin",
                role=User.Role.SUPER_ADMIN,
                is_registration_approved=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Created admin user '{username}'."))
            self.stdout.write(f"  Sign in with: {username} / {password}")
            return

        # Repair flags that would block login or admin access.
        changed = []
        if not user.is_active:
            user.is_active = True
            changed.append("is_active")
        if not user.is_staff:
            user.is_staff = True
            changed.append("is_staff")
        if not user.is_superuser:
            user.is_superuser = True
            changed.append("is_superuser")
        if not getattr(user, "is_registration_approved", True):
            user.is_registration_approved = True
            changed.append("is_registration_approved")
        if getattr(user, "role", None) != User.Role.SUPER_ADMIN:
            user.role = User.Role.SUPER_ADMIN
            changed.append("role")
        if reset_password:
            user.set_password(password)
            changed.append("password")

        if changed:
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Updated admin '{username}': {', '.join(changed)}.")
            )
        else:
            self.stdout.write(f"Admin '{username}' already exists.")
