"""Business logic for administrator-managed employee accounts."""

import secrets
import string

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings

from accounts.services_user_accounts import delete_user_account, set_user_active
from employees.models import Employee

User = get_user_model()

ACCOUNT_ROLE_CHOICES = (
    (User.Role.EMPLOYEE, "Employee"),
    (User.Role.HR_MANAGER, "HR Manager"),
    (User.Role.SUPER_ADMIN, "Administrator"),
)

# Roles HR Managers may assign when creating or editing accounts.
HR_ASSIGNABLE_ROLES = (User.Role.EMPLOYEE, User.Role.HR_MANAGER)


def generate_temporary_password(length=12):
    """Generate a readable temporary password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@transaction.atomic
def create_employee_account(*, form_data, profile_photo=None, created_by=None, existing_employee=None):
    """Create linked Employee + User records in one transaction."""
    password = form_data.get("temporary_password") or generate_temporary_password()

    user = User.objects.create_user(
        username=form_data["username"],
        email=form_data["email"],
        password=password,
        first_name=form_data["first_name"],
        last_name=form_data["last_name"],
        phone=form_data.get("phone_number", ""),
        role=form_data["account_role"],
        is_active=form_data["account_active"],
        is_registration_approved=True,
        must_change_password=True,
    )

    if existing_employee:
        employee = existing_employee
        employee.user = user
    else:
        employee = Employee(user=user)

    employee.first_name = form_data["first_name"]
    employee.middle_name = form_data.get("middle_name", "")
    employee.last_name = form_data["last_name"]
    employee.suffix = form_data.get("suffix", "")
    employee.email = form_data["email"]
    employee.phone_number = form_data.get("phone_number", "")
    employee.date_of_birth = form_data.get("date_of_birth")
    employee.gender = form_data.get("gender", "")
    employee.address = form_data.get("address", "")
    employee.department = form_data["department"]
    employee.position = form_data["position"]
    employee.employment_status = form_data["employment_status"]
    employee.employee_type = form_data["employee_type"]
    employee.date_hired = form_data["date_hired"]
    employee.is_active = form_data["account_active"]
    if profile_photo:
        employee.profile_photo = profile_photo
    employee.save()

    return employee, user, password


@transaction.atomic
def update_employee_account(*, employee, form_data, profile_photo=None, new_password=None):
    """Update employee profile and linked user account."""
    user = employee.user
    if not user:
        raise ValueError("Employee has no linked user account.")

    user.username = form_data["username"]
    user.email = form_data["email"]
    user.first_name = form_data["first_name"]
    user.last_name = form_data["last_name"]
    user.phone = form_data.get("phone_number", "")
    user.role = form_data["account_role"]
    user.is_active = form_data["account_active"]
    if new_password:
        user.set_password(new_password)
        user.must_change_password = True
    user.save()

    employee.first_name = form_data["first_name"]
    employee.middle_name = form_data.get("middle_name", "")
    employee.last_name = form_data["last_name"]
    employee.suffix = form_data.get("suffix", "")
    employee.email = form_data["email"]
    employee.phone_number = form_data.get("phone_number", "")
    employee.date_of_birth = form_data.get("date_of_birth")
    employee.gender = form_data.get("gender", "")
    employee.address = form_data.get("address", "")
    employee.department = form_data["department"]
    employee.position = form_data["position"]
    employee.employment_status = form_data["employment_status"]
    employee.employee_type = form_data["employee_type"]
    employee.date_hired = form_data["date_hired"]
    employee.is_active = form_data["account_active"]
    if profile_photo:
        employee.profile_photo = profile_photo
    employee.save()

    return employee, user


@transaction.atomic
def reset_employee_password(employee):
    """Reset password and require change on next login."""
    user = employee.user
    if not user:
        raise ValueError("Employee has no linked user account.")
    password = generate_temporary_password()
    user.set_password(password)
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password"])
    return password


@transaction.atomic
def set_account_active(employee, *, active: bool):
    """Activate or deactivate employee and user account."""
    if not employee.user_id:
        raise ValueError("Employee has no linked user account.")
    set_user_active(target_user=employee.user, active=active)


@transaction.atomic
def delete_employee_account(employee):
    """Delete employee record and linked user."""
    if not employee.user_id:
        employee.delete()
        return
    delete_user_account(employee.user)


def send_credentials_email(*, employee, username, password, requested_by, login_url=""):
    """Email login credentials to the employee."""
    subject = "Your Employee Directory account"
    body = (
        f"Hello {employee.full_name},\n\n"
        f"An administrator ({requested_by.get_full_name() or requested_by.username}) "
        f"created your Employee Directory account.\n\n"
        f"Employee ID: {employee.employee_id}\n"
        f"Username: {username}\n"
        f"Temporary password: {password}\n\n"
        f"Please sign in and change your password immediately.\n"
    )
    if login_url:
        body += f"\nSign in: {login_url}\n"
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [employee.email],
        fail_silently=False,
    )
