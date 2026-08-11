"""Dashboard views with statistics and charts data."""

import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from attendance.models import LeaveRequest
from attendance.services import count_employees_on_leave, sync_leave_employment_statuses
from departments.models import Department
from employees.models import ActivityLog, CompanyAnnouncement, Employee


def _pct_change(current, previous):
    """Month-over-month percentage change for KPI trend indicators."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _next_birthday(dob, today):
    """Return the next occurrence of a birthday on or after today."""
    try:
        next_bday = dob.replace(year=today.year)
    except ValueError:
        # Feb 29 → Mar 1 on non-leap years
        next_bday = date(today.year, 3, 1)
    if next_bday < today:
        try:
            next_bday = dob.replace(year=today.year + 1)
        except ValueError:
            next_bday = date(today.year + 1, 3, 1)
    return next_bday


def _count_upcoming_birthdays(days=30):
    """Count active employees with birthdays within the next N days."""
    today = date.today()
    count = 0
    for dob in Employee.objects.filter(
        is_active=True,
        date_of_birth__isnull=False,
    ).values_list("date_of_birth", flat=True):
        next_bday = _next_birthday(dob, today)
        if 0 <= (next_bday - today).days <= days:
            count += 1
    return count


def _on_leave_count(for_date):
    """Distinct active employees on approved leave for a given date."""
    return count_employees_on_leave(for_date)


@login_required
def dashboard_home(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    today_date = now.date()
    # Clear stale On Leave badges after the leave end date
    sync_leave_employment_statuses(today_date)

    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(is_active=True).count()
    inactive_employees = Employee.objects.filter(is_active=False).count()
    departments_count = Department.objects.filter(is_active=True).count()
    new_this_month = Employee.objects.filter(created_at__gte=month_start).count()
    recent_hires = Employee.objects.select_related("department", "position").order_by("-date_hired")[:5]

    # KPI extras for glassmorphism stat cards
    upcoming_birthdays = _count_upcoming_birthdays(days=30)
    on_leave_count = _on_leave_count(today_date)
    on_leave_yesterday = _on_leave_count(today_date - timedelta(days=1))

    total_at_month_start = Employee.objects.filter(created_at__lt=month_start).count()
    active_at_month_start = Employee.objects.filter(
        is_active=True, created_at__lt=month_start
    ).count()
    new_last_month = Employee.objects.filter(
        created_at__gte=last_month_start, created_at__lt=month_start
    ).count()
    departments_at_month_start = Department.objects.filter(
        is_active=True, created_at__lt=month_start
    ).count()

    # Prior 30-day birthday window for trend comparison
    prior_birthdays = 0
    for dob in Employee.objects.filter(
        is_active=True, date_of_birth__isnull=False
    ).values_list("date_of_birth", flat=True):
        next_bday = _next_birthday(dob, today_date - timedelta(days=30))
        days_until = (next_bday - (today_date - timedelta(days=30))).days
        if 0 <= days_until <= 30:
            prior_birthdays += 1

    kpi_trends = {
        "total": _pct_change(total_employees, total_at_month_start),
        "active": _pct_change(active_employees, active_at_month_start),
        "departments": _pct_change(departments_count, departments_at_month_start),
        "birthdays": _pct_change(upcoming_birthdays, prior_birthdays),
        "on_leave": _pct_change(on_leave_count, on_leave_yesterday),
        "new_hires": _pct_change(new_this_month, new_last_month),
    }

    # Chart data: employees by department
    dept_chart = list(
        Department.objects.filter(is_active=True)
        .annotate(emp_count=Count("employees", filter=Q(employees__is_active=True)))
        .values("name", "emp_count")
        .order_by("-emp_count")[:8]
    )

    # Chart data: hires by month (last 6 calendar months, by record creation date)
    hire_counts = {}
    for item in (
        Employee.objects.filter(created_at__gte=now - timedelta(days=185))
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
    ):
        if item["month"]:
            hire_counts[item["month"].strftime("%Y-%m")] = item["count"]

    hire_chart = []
    year, month = now.year, now.month
    for _ in range(6):
        key = f"{year:04d}-{month:02d}"
        hire_chart.insert(0, {
            "month": date(year, month, 1).strftime("%b %Y"),
            "count": hire_counts.get(key, 0),
        })
        month -= 1
        if month < 1:
            month = 12
            year -= 1

    # Status breakdown
    status_chart = list(
        Employee.objects.values("employment_status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    announcements = CompanyAnnouncement.objects.filter(is_active=True).select_related("created_by")[:5]

    employees_on_leave = Employee.objects.filter(
        is_active=True,
        leave_requests__status=LeaveRequest.Status.APPROVED,
        leave_requests__start_date__lte=today_date,
        leave_requests__end_date__gte=today_date,
    ).distinct().select_related("department")[:8]

    pending_approvals = LeaveRequest.objects.filter(
        status=LeaveRequest.Status.PENDING
    ).select_related("employee", "leave_type")[:8]

    recent_activities = ActivityLog.objects.select_related("user")[:12]

    active_rate = round((active_employees / total_employees) * 100) if total_employees else 0
    top_department = dept_chart[0]["name"] if dept_chart else "—"
    inactive_rate = round((inactive_employees / total_employees) * 100) if total_employees else 0
    new_hire_bar_width = min(new_this_month * 10, 100) if new_this_month else 0
    dept_bar_width = min(round((departments_count / 12) * 100), 100) if departments_count else 0

    context = {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "inactive_employees": inactive_employees,
        "departments_count": departments_count,
        "new_this_month": new_this_month,
        "upcoming_birthdays": upcoming_birthdays,
        "on_leave_count": on_leave_count,
        "kpi_trends": kpi_trends,
        "active_rate": active_rate,
        "inactive_rate": inactive_rate,
        "new_hire_bar_width": new_hire_bar_width,
        "dept_bar_width": dept_bar_width,
        "top_department": top_department,
        "recent_hires": recent_hires,
        "dept_chart_json": json.dumps(dept_chart),
        "hire_chart_json": json.dumps(hire_chart),
        "status_chart_json": json.dumps(status_chart),
        "announcements": announcements,
        "employees_on_leave": employees_on_leave,
        "pending_approvals": pending_approvals,
        "recent_activities": recent_activities,
        "today": now,
    }
    return render(request, "dashboard/home.html", context)


@login_required
def settings_view(request):
    """Settings hub — preferences, account shortcuts, and admin tools."""
    return render(request, "dashboard/settings.html")
