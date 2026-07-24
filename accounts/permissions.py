"""Role-based permission helpers and decorators."""

from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Decorator restricting access to specific user roles."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.is_super_admin:
                return view_func(request, *args, **kwargs)
            if user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not have permission to access this page.")

        return wrapper

    return decorator


def super_admin_required(view_func):
    return role_required("super_admin")(view_func)


def hr_manager_required(view_func):
    return role_required("super_admin", "hr_manager")(view_func)


def can_manage_employees(user):
    return user.is_authenticated and user.can_manage_employees()


def can_manage_departments(user):
    return user.is_authenticated and user.can_manage_departments()


def can_manage_positions(user):
    return user.is_authenticated and user.can_manage_positions()


def can_manage_users(user):
    return user.is_authenticated and user.can_manage_users()


def can_manage_employee_accounts(user):
    return user.is_authenticated and user.can_manage_employee_accounts()


def can_manage_calendar(user):
    return user.is_authenticated and user.can_manage_calendar()


employee_manager_required = user_passes_test(can_manage_employees)
department_manager_required = user_passes_test(can_manage_departments)
position_manager_required = user_passes_test(can_manage_positions)
user_manager_required = user_passes_test(can_manage_users)
calendar_manager_required = user_passes_test(can_manage_calendar)


def employee_account_admin_required(view_func):
    """Super Admin or HR Manager access for employee account management."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not can_manage_employee_accounts(request.user):
            raise PermissionDenied(
                "Super Admin or HR Manager access is required to manage employee accounts."
            )
        return view_func(request, *args, **kwargs)

    return wrapper
