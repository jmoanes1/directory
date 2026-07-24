"""Attendance time helpers — always use local wall-clock time for punches."""

from datetime import date, datetime, timedelta

from django.utils import timezone


def local_now():
    """Current timezone-aware datetime in the active Django TIME_ZONE."""
    return timezone.localtime(timezone.now())


def local_today():
    """Today's date in the active Django TIME_ZONE."""
    return local_now().date()


def local_time_now():
    """Current local time (no microseconds) for attendance punches."""
    return local_now().time().replace(microsecond=0)


def resolve_punch_datetime(client_time_raw=None, max_drift_seconds=120):
    """
    Resolve punch date/time from client click timestamp or server clock.

    Uses the client time when it is within max_drift_seconds of server local time
    so the saved value matches what the user saw when clicking the button.
    """
    server_dt = local_now().replace(microsecond=0)

    if not client_time_raw:
        return server_dt.date(), server_dt.time()

    client_time_raw = client_time_raw.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            client_naive = datetime.strptime(client_time_raw, fmt)
            break
        except ValueError:
            client_naive = None

    if client_naive is None:
        return server_dt.date(), server_dt.time()

    tz = timezone.get_current_timezone()
    client_dt = timezone.make_aware(client_naive, tz)
    drift = abs((client_dt - server_dt).total_seconds())

    if drift <= max_drift_seconds:
        return client_dt.date(), client_dt.time().replace(microsecond=0)

    return server_dt.date(), server_dt.time()


def parse_work_mode(value, default="office"):
    """Validate work mode from form POST."""
    allowed = {"office", "wfh"}
    if value in allowed:
        return value
    return default


def format_duration_hours(hours):
    """Format decimal hours as '8h 30m'."""
    if hours is None:
        return "—"
    total_minutes = int(round(float(hours) * 60))
    h, m = divmod(total_minutes, 60)
    if m:
        return f"{h}h {m}m"
    return f"{h}h"


def format_time_value(time_value):
    """Format a time value with seconds for accurate display."""
    if not time_value:
        return "—"
    return time_value.strftime("%H:%M:%S")


def get_period_bounds(period, anchor=None):
    """
    Return (start_date, end_date, label) for week or month timesheet views.
    Weeks start on Monday.
    """
    anchor = anchor or local_today()

    if period == "month":
        start = anchor.replace(day=1)
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
        label = start.strftime("%B %Y")
        return start, end, label

    # Default: calendar week (Mon–Sun)
    start = anchor - timedelta(days=anchor.weekday())
    end = start + timedelta(days=6)
    label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    return start, end, label


def shift_period(period, anchor, direction):
    """Move anchor date to previous (-1) or next (+1) week/month."""
    if period == "month":
        month_index = anchor.year * 12 + (anchor.month - 1) + direction
        year, month = divmod(month_index, 12)
        month += 1
        return date(year, month, 1)
    return anchor + timedelta(weeks=direction)


def build_timesheet_summary(records):
    """Aggregate hours and attendance counts for a timesheet period."""
    total_hours = 0.0
    complete_days = 0
    partial_days = 0

    for record in records:
        hours = record.hours_worked
        if hours:
            total_hours += hours
            if record.is_day_complete:
                complete_days += 1
            else:
                partial_days += 1

    days_with_punches = len([r for r in records if r.time_in_morning])
    avg_hours = round(total_hours / days_with_punches, 2) if days_with_punches else 0

    return {
        "total_hours": round(total_hours, 2),
        "total_hours_display": format_duration_hours(total_hours),
        "complete_days": complete_days,
        "partial_days": partial_days,
        "days_with_punches": days_with_punches,
        "average_hours": avg_hours,
        "average_hours_display": format_duration_hours(avg_hours),
    }
