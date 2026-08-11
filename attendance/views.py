"""Attendance and leave management views."""

from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.permissions import hr_manager_required
from attendance.forms import AttendanceCheckForm, LeaveRequestForm, LeaveReviewForm
from attendance.models import AttendanceRecord, LeaveRequest
from attendance.services import (
    count_employees_on_leave,
    get_leave_balances,
    send_leave_approval_email_async,
    serialize_leave_balances,
    sync_employee_leave_status,
    sync_leave_employment_statuses,
)
from attendance.time_utils import (
    build_timesheet_summary,
    format_timezone_label,
    get_period_bounds,
    local_now,
    local_today,
    parse_work_mode,
    resolve_punch_datetime,
    shift_period,
)
from employees.models import Employee
from employees.utils import log_activity
from notifications.models import Notification
from notifications.utils import notify_hr_managers, notify_user

PUNCH_SEQUENCE = (
    "time_in_morning",
    "break_lunch",
    "time_in_noon",
    "time_out_afternoon",
)

PUNCH_LABELS = dict(AttendanceRecord.PUNCH_FIELDS)


def _get_employee_for_user(user):
    """Resolve employee profile linked to the logged-in user."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.employee_profile
    except Employee.DoesNotExist:
        return None


def _parse_anchor_date(raw_value):
    """Parse YYYY-MM-DD from query params, falling back to today."""
    if not raw_value:
        return local_today()
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        return local_today()


@login_required
def attendance_dashboard(request):
    today = local_today()
    # Drop "On Leave" once the approved leave end date has passed
    sync_leave_employment_statuses(today)
    employee = _get_employee_for_user(request.user)
    today_record = None
    if employee:
        today_record = AttendanceRecord.objects.filter(employee=employee, date=today).first()

    recent_records = []
    if employee:
        recent_records = AttendanceRecord.objects.filter(employee=employee).order_by("-date")[:10]

    present_today = AttendanceRecord.objects.filter(date=today, status=AttendanceRecord.Status.PRESENT).count()
    on_leave_today = count_employees_on_leave(today)
    pending_leaves = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count()

    check_form = AttendanceCheckForm()
    leave_balances = get_leave_balances(employee) if employee else []
    punch_actions = [
        {
            "key": key,
            "label": label,
            "time": getattr(today_record, key, None) if today_record else None,
            "is_next": today_record.next_punch_action == key if today_record else key == "time_in_morning",
            "is_done": bool(getattr(today_record, key, None)) if today_record else False,
        }
        for key, label in AttendanceRecord.PUNCH_FIELDS
    ]

    now = local_now()
    selected_work_mode = today_record.work_mode if today_record else AttendanceRecord.WorkMode.OFFICE

    return render(request, "attendance/dashboard.html", {
        "employee": employee,
        "today_record": today_record,
        "recent_records": recent_records,
        "present_today": present_today,
        "on_leave_today": on_leave_today,
        "pending_leaves": pending_leaves,
        "leave_balances": leave_balances,
        "check_form": check_form,
        "punch_actions": punch_actions,
        "selected_work_mode": selected_work_mode,
        "work_mode_choices": AttendanceRecord.WorkMode.choices,
        "can_manage": request.user.can_manage_employees(),
        "current_local_time": now.time(),
        "timezone_label": format_timezone_label(now.tzinfo),
        "server_timestamp_ms": int(now.timestamp() * 1000),
    })


@login_required
@require_POST
def attendance_punch(request):
    """Record the next attendance time slot using the exact client click time."""
    employee = _get_employee_for_user(request.user)
    if not employee:
        messages.error(request, "No employee profile linked to your account.")
        return redirect("attendance:dashboard")

    action = request.POST.get("action", "")
    if action not in PUNCH_SEQUENCE:
        messages.error(request, "Invalid attendance action.")
        return redirect("attendance:dashboard")

    punch_date, punch_time = resolve_punch_datetime(request.POST.get("client_time"))
    work_mode = parse_work_mode(request.POST.get("work_mode"))

    record, _created = AttendanceRecord.objects.get_or_create(
        employee=employee,
        date=punch_date,
        defaults={"status": AttendanceRecord.Status.PRESENT, "work_mode": work_mode},
    )

    expected_action = record.next_punch_action
    if expected_action != action:
        if record.is_day_complete:
            messages.warning(request, "Today's attendance is already complete.")
        elif expected_action:
            messages.warning(
                request,
                f"Please complete {PUNCH_LABELS[expected_action]} first.",
            )
        else:
            messages.warning(request, "This attendance action is not available.")
        return redirect("attendance:dashboard")

    if not record.time_in_morning or action == "time_in_morning":
        record.work_mode = work_mode

    setattr(record, action, punch_time)
    record.status = AttendanceRecord.Status.PRESENT
    record.save(update_fields=[action, "work_mode", "status", "updated_at"])

    time_label = punch_time.strftime("%H:%M:%S")
    mode_label = record.get_work_mode_display()
    log_activity(
        request,
        "create" if action == "time_in_morning" else "update",
        f"{PUNCH_LABELS[action]} at {time_label} ({mode_label})",
        "AttendanceRecord",
        record.pk,
    )

    if action == "time_out_afternoon":
        messages.success(
            request,
            f"{PUNCH_LABELS[action]} recorded at {time_label} ({mode_label}). Total: {record.hours_worked_display}",
        )
    else:
        messages.success(request, f"{PUNCH_LABELS[action]} recorded at {time_label} ({mode_label})")

    return redirect("attendance:dashboard")


@login_required
def timesheet_view(request):
    """Weekly or monthly timesheet for the logged-in employee."""
    employee = _get_employee_for_user(request.user)
    if not employee:
        messages.error(request, "No employee profile linked to your account.")
        return redirect("attendance:dashboard")

    period = request.GET.get("period", "week")
    if period not in ("week", "month"):
        period = "week"

    anchor_date = _parse_anchor_date(request.GET.get("date"))
    start_date, end_date, period_label = get_period_bounds(period, anchor_date)

    records = list(
        AttendanceRecord.objects.filter(
            employee=employee,
            date__gte=start_date,
            date__lte=end_date,
        ).order_by("-date")
    )
    summary = build_timesheet_summary(records)
    now = local_now()

    return render(request, "attendance/timesheet.html", {
        "employee": employee,
        "records": records,
        "summary": summary,
        "period": period,
        "period_label": period_label,
        "anchor_date": anchor_date,
        "prev_anchor": shift_period(period, anchor_date, -1),
        "next_anchor": shift_period(period, anchor_date, 1),
        "current_local_time": now.time(),
        "timezone_label": format_timezone_label(now.tzinfo),
        "server_timestamp_ms": int(now.timestamp() * 1000),
    })


@login_required
def leave_list_view(request):
    today = local_today()
    sync_leave_employment_statuses(today)
    employee = _get_employee_for_user(request.user)
    if request.user.can_manage_employees():
        leaves = LeaveRequest.objects.select_related("employee", "leave_type", "reviewed_by").all()
    elif employee:
        leaves = LeaveRequest.objects.filter(employee=employee).select_related("leave_type", "reviewed_by")
    else:
        leaves = LeaveRequest.objects.none()

    leave_balances = get_leave_balances(employee) if employee else []
    pending_count = leaves.filter(status=LeaveRequest.Status.PENDING).count()
    approved_days = sum(
        leave.total_days
        for leave in leaves.filter(status=LeaveRequest.Status.APPROVED)
    )
    on_leave_count = count_employees_on_leave(today)

    return render(request, "attendance/leave_list.html", {
        "leaves": leaves,
        "can_manage": request.user.can_manage_employees(),
        "leave_balances": leave_balances,
        "pending_count": pending_count,
        "approved_days": approved_days,
        "on_leave_count": on_leave_count,
    })


@login_required
def leave_request_view(request):
    employee = _get_employee_for_user(request.user)
    can_manage = request.user.can_manage_employees()

    if not employee and not can_manage:
        messages.error(request, "No employee profile linked to your account.")
        return redirect("attendance:leave_list")

    form = LeaveRequestForm(request.POST or None, user=request.user, linked_employee=employee)
    leave_balances = get_leave_balances(employee) if employee else []
    form_context = {
        "form": form,
        "employee": employee,
        "leave_balances": leave_balances,
        "leave_balances_json": serialize_leave_balances(leave_balances),
        "can_manage": can_manage,
    }
    if request.method == "POST" and form.is_valid():
        leave = form.save(commit=False)
        # HR/admin pick the employee on the form; everyone else uses their linked profile.
        leave.employee = form.cleaned_data.get("employee") or employee
        if not leave.employee_id:
            messages.error(request, "Select an employee for this leave request.")
            return render(request, "attendance/leave_form.html", form_context)
        leave.save()
        notify_hr_managers(
            title="New Leave Request",
            message=f"{leave.employee.full_name} requested {leave.leave_type.name} ({leave.start_date} – {leave.end_date})",
            notification_type=Notification.Type.LEAVE,
            link=reverse("attendance:leave_list"),
        )
        log_activity(request, "create", f"Leave request: {leave.leave_type.name}", "LeaveRequest", leave.pk)
        messages.success(request, "Leave request submitted successfully.")
        return redirect("attendance:leave_list")

    return render(request, "attendance/leave_form.html", form_context)


@login_required
def leave_balances_api(request, employee_id):
    """Return leave balances for the request form (HR employee picker)."""
    target = get_object_or_404(Employee, pk=employee_id, is_active=True)
    linked = _get_employee_for_user(request.user)

    if not request.user.can_manage_employees():
        if not linked or linked.pk != target.pk:
            return JsonResponse({"error": "Forbidden"}, status=403)

    balances = serialize_leave_balances(get_leave_balances(target))
    return JsonResponse({"balances": balances})


@hr_manager_required
@require_POST
def leave_review_view(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    form = LeaveReviewForm(request.POST)
    if form.is_valid():
        previous_status = leave.status
        leave.status = form.cleaned_data["action"]
        leave.reviewed_by = request.user
        leave.review_notes = form.cleaned_data.get("review_notes", "")
        leave.save()

        employee_user = getattr(leave.employee, "user", None)
        if employee_user:
            notify_user(
                employee_user,
                title=f"Leave {leave.get_status_display()}",
                message=f"Your {leave.leave_type.name} request ({leave.start_date} – {leave.end_date}) was {leave.status}.",
                notification_type=Notification.Type.LEAVE,
                link=reverse("attendance:leave_list"),
            )

        # Set On Leave only while dates cover today; restore Active after end date
        sync_employee_leave_status(leave.employee)

        should_send_approval_email = (
            previous_status == LeaveRequest.Status.PENDING
            and leave.status == LeaveRequest.Status.APPROVED
            and leave.approval_email_sent_at is None
        )
        if should_send_approval_email:
            leave.approval_email_sent_at = timezone.now()
            leave.save(update_fields=["approval_email_sent_at", "updated_at"])
            send_leave_approval_email_async(leave.pk)

        log_activity(request, "update", f"Leave {leave.status}: {leave.employee.full_name}", "LeaveRequest", leave.pk)
        messages.success(request, f"Leave request {leave.status}.")
    return redirect("attendance:leave_list")


@login_required
def attendance_report_view(request):
    if not request.user.can_manage_employees():
        messages.error(request, "Permission denied.")
        return redirect("attendance:dashboard")

    month_start = local_today().replace(day=1)
    records = AttendanceRecord.objects.filter(
        date__gte=month_start
    ).select_related("employee").order_by("-date")

    summary = records.values("status").annotate(count=Count("id"))

    return render(request, "attendance/report.html", {
        "records": records[:50],
        "summary": summary,
        "month_start": month_start,
    })
