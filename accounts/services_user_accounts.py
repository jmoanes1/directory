"""Administrator actions for system user accounts."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q

User = get_user_model()


def _is_admin_user(user):
    return user.is_super_admin or user.is_superuser


def _active_admin_count(*, exclude_pk=None):
    qs = User.objects.filter(is_active=True).filter(
        Q(role=User.Role.SUPER_ADMIN) | Q(is_superuser=True)
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def _admin_count(*, exclude_pk=None):
    qs = User.objects.filter(Q(role=User.Role.SUPER_ADMIN) | Q(is_superuser=True))
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def validate_user_account_action(*, actor, target, action):
    """
    Guardrails for deactivate/delete.
    action: 'deactivate' | 'delete'
    """
    if actor.pk == target.pk:
        raise PermissionDenied("You cannot modify your own account.")

    if target.is_superuser and not actor.is_superuser:
        raise PermissionDenied("Only a Django superuser can modify superuser accounts.")

    if target.is_super_admin and not actor.is_super_admin:
        raise PermissionDenied("Only a Super Admin can modify administrator accounts.")

    if not _is_admin_user(target):
        return

    if action == "deactivate" and target.is_active:
        if _active_admin_count(exclude_pk=target.pk) == 0:
            raise PermissionDenied("Cannot deactivate the last active administrator account.")

    if action == "delete" and _admin_count(exclude_pk=target.pk) == 0:
        raise PermissionDenied("Cannot delete the last administrator account.")


@transaction.atomic
def set_user_active(*, target_user, active: bool):
    """Activate or deactivate a user and linked employee record."""
    target_user.is_active = active
    target_user.save(update_fields=["is_active"])

    profile = getattr(target_user, "employee_profile", None)
    if profile:
        profile.is_active = active
        profile.save(update_fields=["is_active"])


@transaction.atomic
def delete_user_account(target_user):
    """Delete user and linked employee profile when present."""
    profile = getattr(target_user, "employee_profile", None)
    if profile:
        profile.delete()
    target_user.delete()
