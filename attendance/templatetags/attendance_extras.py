"""Template filters for attendance display."""

from django import template

from attendance.time_utils import format_duration_hours, format_time_value

register = template.Library()


@register.filter
def attendance_time(value):
    """Render punch time with seconds."""
    return format_time_value(value)


@register.filter
def duration_hours(value):
    """Render decimal hours as '8h 30m'."""
    return format_duration_hours(value)
