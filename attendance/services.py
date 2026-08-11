"""Attendance domain services (balances, leave status sync, notifications)."""

from datetime import date
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Exists, OuterRef
from django.utils import timezone

from attendance.models import LeaveRequest, LeaveType
from employees.models import Employee

logger = logging.getLogger(__name__)


def employee_has_active_leave(employee, for_date=None):
    """True when the employee has approved leave covering for_date (default: today)."""
    if not employee:
        return False
    for_date = for_date or date.today()
    return LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
        start_date__lte=for_date,
        end_date__gte=for_date,
    ).exists()


def count_employees_on_leave(for_date=None):
    """Distinct active employees on approved leave for a given date."""
    for_date = for_date or date.today()
    return Employee.objects.filter(
        is_active=True,
        leave_requests__status=LeaveRequest.Status.APPROVED,
        leave_requests__start_date__lte=for_date,
        leave_requests__end_date__gte=for_date,
    ).distinct().count()


def sync_employee_leave_status(employee, for_date=None):
    """
    Keep employment/availability status in sync with approved leave dates.
    - During leave window → On Leave
    - After end date (or before start) → restore Active / Available
    Does not change Inactive or Terminated employment status.
    """
    if not employee:
        return employee

    for_date = for_date or date.today()
    on_leave_now = employee_has_active_leave(employee, for_date)
    update_fields = []

    # Never override inactive/terminated records when leave ends
    locked = employee.employment_status in (
        Employee.EmploymentStatus.INACTIVE,
        Employee.EmploymentStatus.TERMINATED,
    )

    if on_leave_now and not locked:
        if employee.employment_status != Employee.EmploymentStatus.ON_LEAVE:
            employee.employment_status = Employee.EmploymentStatus.ON_LEAVE
            update_fields.append("employment_status")
        if employee.availability_status != Employee.AvailabilityStatus.ON_LEAVE:
            employee.availability_status = Employee.AvailabilityStatus.ON_LEAVE
            update_fields.append("availability_status")
    else:
        if employee.employment_status == Employee.EmploymentStatus.ON_LEAVE:
            employee.employment_status = Employee.EmploymentStatus.ACTIVE
            update_fields.append("employment_status")
        if employee.availability_status == Employee.AvailabilityStatus.ON_LEAVE:
            employee.availability_status = Employee.AvailabilityStatus.AVAILABLE
            update_fields.append("availability_status")

    if update_fields:
        update_fields.append("updated_at")
        employee.save(update_fields=update_fields)

    return employee


def sync_leave_employment_statuses(for_date=None):
    """
    Bulk sync: clear On Leave after the leave end date, and mark currently
    covered employees as On Leave. Safe to call from dashboards/list views.
    """
    for_date = for_date or date.today()

    active_leave = LeaveRequest.objects.filter(
        employee_id=OuterRef("pk"),
        status=LeaveRequest.Status.APPROVED,
        start_date__lte=for_date,
        end_date__gte=for_date,
    )

    # Restore employees stuck on On Leave after their leave window ended
    expired_qs = (
        Employee.objects.filter(employment_status=Employee.EmploymentStatus.ON_LEAVE)
        .annotate(has_active_leave=Exists(active_leave))
        .filter(has_active_leave=False)
    )
    expired_ids = list(expired_qs.values_list("pk", flat=True))
    if expired_ids:
        Employee.objects.filter(pk__in=expired_ids).update(
            employment_status=Employee.EmploymentStatus.ACTIVE,
            updated_at=timezone.now(),
        )
        # Clear leave availability only when it was leave-driven
        Employee.objects.filter(
            pk__in=expired_ids,
            availability_status=Employee.AvailabilityStatus.ON_LEAVE,
        ).update(
            availability_status=Employee.AvailabilityStatus.AVAILABLE,
            updated_at=timezone.now(),
        )

    # Promote employees whose approved leave covers today
    starting_qs = (
        Employee.objects.exclude(
            employment_status__in=[
                Employee.EmploymentStatus.INACTIVE,
                Employee.EmploymentStatus.TERMINATED,
                Employee.EmploymentStatus.ON_LEAVE,
            ]
        )
        .annotate(has_active_leave=Exists(active_leave))
        .filter(has_active_leave=True)
    )
    starting_ids = list(starting_qs.values_list("pk", flat=True))
    if starting_ids:
        Employee.objects.filter(pk__in=starting_ids).update(
            employment_status=Employee.EmploymentStatus.ON_LEAVE,
            availability_status=Employee.AvailabilityStatus.ON_LEAVE,
            updated_at=timezone.now(),
        )

    return {"restored": len(expired_ids), "marked_on_leave": len(starting_ids)}


def _days_in_year(start, end, year):
    """Count leave days falling within a calendar year."""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    overlap_start = max(start, year_start)
    overlap_end = min(end, year_end)
    if overlap_end < overlap_start:
        return 0
    return (overlap_end - overlap_start).days + 1


def get_leave_balances(employee, year=None):
    """
    Return leave balance rows for an employee.
    Each row: leave_type, entitled, used, remaining.
    """
    if not employee:
        return []

    year = year or date.today().year
    balances = []

    approved = LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
    ).select_related("leave_type")

    for leave_type in LeaveType.objects.filter(is_active=True):
        entitled = leave_type.max_days_per_year
        used = sum(
            _days_in_year(req.start_date, req.end_date, year)
            for req in approved
            if req.leave_type_id == leave_type.pk
        )
        balances.append({
            "leave_type": leave_type,
            "entitled": entitled,
            "used": used,
            "remaining": max(0, entitled - used),
        })

    return balances


def serialize_leave_balances(balances):
    """Serialize balance rows for JSON/API and client-side leave count hints."""
    return [
        {
            "leave_type_id": row["leave_type"].pk,
            "name": row["leave_type"].name,
            "color": row["leave_type"].color,
            "entitled": row["entitled"],
            "used": row["used"],
            "remaining": row["remaining"],
        }
        for row in balances
    ]


def _resolve_leave_recipient_email(leave):
    """
    Resolve recipient email for leave notifications.
    Prefer linked user email (account-registered) when present; fallback to employee profile email.
    """
    employee_email = (leave.employee.email or "").strip()
    user_email = ""
    if leave.employee.user_id:
        user_email = (leave.employee.user.email or "").strip()

    if user_email and employee_email and user_email.lower() != employee_email.lower():
        logger.warning(
            "Leave email mismatch for leave %s: employee.email=%s user.email=%s; using user email.",
            leave.pk,
            employee_email,
            user_email,
        )

    return user_email or employee_email


def _send_leave_approval_email(leave_request_id):
    """Send approved leave email using existing SMTP settings."""
    leave = (
        LeaveRequest.objects.select_related("employee", "leave_type", "reviewed_by")
        .filter(pk=leave_request_id)
        .first()
    )
    if not leave:
        logger.error("Leave approval email skipped: leave %s not found.", leave_request_id)
        return

    recipient = _resolve_leave_recipient_email(leave)
    if not recipient:
        logger.error(
            "Leave approval email skipped: no employee email for leave %s.",
            leave_request_id,
        )
        return

    approver_name = "HR"
    if leave.reviewed_by:
        approver_name = leave.reviewed_by.get_full_name() or leave.reviewed_by.username

    approval_date = timezone.localtime(leave.approval_email_sent_at or timezone.now()).date()
    subject = "Leave Request Approved"
    body = (
        f"Hello {leave.employee.full_name},\n\n"
        "Your leave request has been approved by HR.\n\n"
        "Leave Details:\n\n"
        f"Leave Type: {leave.leave_type.name}\n"
        f"Start Date: {leave.start_date}\n"
        f"End Date: {leave.end_date}\n"
        f"Total Days: {leave.total_days}\n"
        f"Approved By: {approver_name}\n"
        f"Approval Date: {approval_date}\n\n"
        "You may log in to the Employee Portal to view the complete details of your approved leave.\n\n"
        "Thank you,\n"
        "HR Department"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info(
            "Leave approval email sent for leave %s to %s.",
            leave_request_id,
            recipient,
        )
    except Exception:
        logger.exception(
            "Leave approval email failed for leave %s to %s.",
            leave_request_id,
            recipient,
        )


def send_leave_approval_email_async(leave_request_id):
    """Dispatch leave approval email in a background thread."""
    threading.Thread(
        target=_send_leave_approval_email,
        args=(leave_request_id,),
        daemon=True,
        name=f"leave-approval-email-{leave_request_id}",
    ).start()
