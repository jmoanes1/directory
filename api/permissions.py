"""REST API permission classes."""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsHRManagerOrReadOnly(BasePermission):
    """Allow read access to authenticated users; write access to HR/Admin."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.can_manage_employees()


class IsDepartmentManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.can_manage_departments()


class IsPositionManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.can_manage_positions()
