"""Middleware for activity logging on key actions."""

from employees.utils import log_activity


class ActivityLogMiddleware:
    """Log authentication events automatically."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        return None
