"""Employee views: CRUD, directory, exports, QR codes."""

import io
from datetime import datetime

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from accounts.permissions import employee_account_admin_required, employee_manager_required, hr_manager_required
from departments.models import Department
from employees.forms import AnnouncementForm, EmployeeForm
from employees.forms_portal import RecognitionForm, TimelineEventForm
from employees.models import (
    ActivityLog, CompanyAnnouncement, Employee,
    EmployeeDocument, EmployeeRecognition, EmployeeTimelineEvent,
)
from employees.utils import log_activity
from attendance.services import get_leave_balances, sync_leave_employment_statuses
from positions.models import Position

PER_PAGE_OPTIONS = (12, 24, 48, 96)


def _get_per_page(request):
    """Resolve a safe page size from the query string."""
    try:
        per_page = int(request.GET.get("per_page", settings.EMPLOYEES_PER_PAGE))
    except (TypeError, ValueError):
        per_page = settings.EMPLOYEES_PER_PAGE
    if per_page not in PER_PAGE_OPTIONS:
        per_page = settings.EMPLOYEES_PER_PAGE
    return per_page


def _page_window(page_obj, radius=2):
    """Build a compact page list with ellipsis markers (None)."""
    total = page_obj.paginator.num_pages
    current = page_obj.number
    if total <= 1:
        return []

    start = max(1, current - radius)
    end = min(total, current + radius)
    pages = []

    if start > 1:
        pages.append(1)
        if start > 2:
            pages.append(None)

    pages.extend(range(start, end + 1))

    if end < total:
        if end < total - 1:
            pages.append(None)
        pages.append(total)

    return pages


def _pagination_meta(page_obj):
    """Shared pagination metadata for templates and AJAX responses."""
    paginator = page_obj.paginator
    count = paginator.count
    return {
        "total_count": count,
        "num_pages": paginator.num_pages,
        "current_page": page_obj.number,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "start_index": page_obj.start_index() if count else 0,
        "end_index": page_obj.end_index() if count else 0,
        "page_window": _page_window(page_obj),
    }


def _serialize_employee(emp):
    """Serialize employee directory row data for AJAX responses."""
    photo_url = emp.profile_photo.url if emp.profile_photo else ""
    return {
        "id": emp.pk,
        "employee_id": emp.employee_id,
        "first_name": emp.first_name,
        "middle_name": emp.middle_name,
        "last_name": emp.last_name,
        "full_name": emp.full_name,
        "email": emp.email,
        "phone": emp.phone_number,
        "department": emp.department.name,
        "position": emp.position.title,
        "manager": emp.manager.full_name if emp.manager else "",
        "status": emp.get_employment_status_display(),
        "status_code": emp.employment_status,
        "is_active": emp.is_active,
        "initials": emp.initials,
        "photo_url": photo_url,
        "linkedin_url": emp.linkedin_url or "",
        "qr_url": reverse("employees:qr", kwargs={"pk": emp.pk}),
        "detail_url": reverse("employees:detail", kwargs={"pk": emp.pk}),
    }


def _get_employee_queryset(request):
    """Build filtered and sorted employee queryset from request params."""
    qs = Employee.objects.select_related("department", "position", "manager").all()

    search = request.GET.get("search", "").strip()
    department = request.GET.get("department", "")
    position = request.GET.get("position", "")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "last_name")

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(employee_id__icontains=search)
            | Q(phone_number__icontains=search)
        )
    if department:
        qs = qs.filter(department_id=department)
    if position:
        qs = qs.filter(position_id=position)
    if status:
        qs = qs.filter(employment_status=status)

    sort_map = {
        "last_name": "last_name",
        "-last_name": "-last_name",
        "first_name": "first_name",
        "date_hired": "date_hired",
        "-date_hired": "-date_hired",
        "department": "department__name",
        "employee_id": "employee_id",
    }
    qs = qs.order_by(sort_map.get(sort, "last_name"))
    return qs


@login_required
def employee_list_view(request):
    # Keep directory badges accurate after leave end dates pass
    sync_leave_employment_statuses()
    view_mode = request.GET.get("view", "card")
    per_page = _get_per_page(request)
    queryset = _get_employee_queryset(request)
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))
    pagination = _pagination_meta(page_obj)

    context = {
        "page_obj": page_obj,
        "employees": page_obj,
        "pagination": pagination,
        "per_page_options": PER_PAGE_OPTIONS,
        "view_mode": view_mode,
        "departments": Department.objects.filter(is_active=True),
        "positions": Position.objects.filter(is_active=True),
        "status_choices": Employee.EmploymentStatus.choices,
        "filters": {
            "search": request.GET.get("search", ""),
            "department": request.GET.get("department", ""),
            "position": request.GET.get("position", ""),
            "status": request.GET.get("status", ""),
            "sort": request.GET.get("sort", "last_name"),
            "per_page": per_page,
        },
        "can_manage": request.user.can_manage_employees(),
    }
    return render(request, "employees/list.html", context)


@login_required
@require_GET
def employee_search_ajax(request):
    """AJAX endpoint for instant employee search."""
    per_page = _get_per_page(request)
    queryset = _get_employee_queryset(request)
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return JsonResponse({
        "employees": [_serialize_employee(emp) for emp in page_obj],
        **_pagination_meta(page_obj),
        "per_page": per_page,
    })


@login_required
def employee_detail_view(request, pk):
    employee = get_object_or_404(
        Employee.objects.select_related("department", "position", "manager", "user").prefetch_related(
            "skills__skill", "documents", "timeline_events", "recognitions",
        ),
        pk=pk,
    )
    activity_logs = ActivityLog.objects.filter(
        model_name="Employee", object_id=str(employee.pk)
    ).select_related("user")[:20]

    log_activity(
        request, "view", f"Viewed employee {employee.full_name}",
        "Employee", employee.pk, employee.full_name,
    )

    return render(request, "employees/detail.html", {
        "employee": employee,
        "activity_logs": activity_logs,
        "can_manage": request.user.can_manage_employees(),
        "leave_balances": get_leave_balances(employee),
    })


@employee_manager_required
def employee_create_view(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        employee = form.save()
        log_activity(
            request, "create", f"Created employee {employee.full_name}",
            "Employee", employee.pk, employee.full_name,
        )
        messages.success(request, f"Employee {employee.full_name} created successfully.")
        return redirect("employees:detail", pk=employee.pk)

    return render(request, "employees/form.html", {"form": form, "title": "Add Employee"})


@employee_account_admin_required
def employee_create_account_view(request, pk):
    """Redirect legacy route to unified admin employee accounts flow."""
    return redirect(f"{reverse('accounts:employee_account_create')}?employee={pk}")


@employee_manager_required
def employee_edit_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=employee)
    if request.method == "POST" and form.is_valid():
        employee = form.save()
        log_activity(
            request, "update", f"Updated employee {employee.full_name}",
            "Employee", employee.pk, employee.full_name,
        )
        messages.success(request, f"Employee {employee.full_name} updated successfully.")
        return redirect("employees:detail", pk=employee.pk)

    return render(request, "employees/form.html", {
        "form": form, "employee": employee, "title": "Edit Employee",
    })


@employee_manager_required
@require_POST
def employee_delete_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    name = employee.full_name
    emp_id = employee.pk
    employee.delete()
    log_activity(request, "delete", f"Deleted employee {name}", "Employee", emp_id, name)
    messages.success(request, f"Employee {name} deleted successfully.")
    return redirect("employees:list")


@employee_manager_required
@require_POST
def employee_toggle_active_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    employee.is_active = not employee.is_active
    if not employee.is_active:
        employee.employment_status = Employee.EmploymentStatus.INACTIVE
    else:
        employee.employment_status = Employee.EmploymentStatus.ACTIVE
    employee.save()

    action = "activate" if employee.is_active else "deactivate"
    log_activity(
        request, action, f"{'Activated' if employee.is_active else 'Deactivated'} employee {employee.full_name}",
        "Employee", employee.pk, employee.full_name,
    )
    status = "activated" if employee.is_active else "deactivated"
    messages.success(request, f"Employee {employee.full_name} {status}.")
    return redirect("employees:detail", pk=employee.pk)


@login_required
def employee_qr_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    profile_url = request.build_absolute_uri(reverse("employees:detail", kwargs={"pk": pk}))

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(profile_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="{employee.employee_id}_qr.png"'
    return response


@login_required
def employee_export_excel(request):
    queryset = _get_employee_queryset(request)
    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"
    headers = [
        "Employee ID", "First Name", "Middle Name", "Last Name", "Email",
        "Phone", "Department", "Position", "Status", "Date Hired",
    ]
    ws.append(headers)

    for emp in queryset:
        ws.append([
            emp.employee_id, emp.first_name, emp.middle_name, emp.last_name,
            emp.email, emp.phone_number, emp.department.name, emp.position.title,
            emp.get_employment_status_display(), emp.date_hired.strftime("%Y-%m-%d"),
        ])

    log_activity(request, "export", f"Exported {queryset.count()} employees to Excel", "Employee")
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="employees_{datetime.now():%Y%m%d}.xlsx"'
    wb.save(response)
    return response


@login_required
def employee_export_pdf(request):
    queryset = _get_employee_queryset(request)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Employee Directory Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]),
        Spacer(1, 20),
    ]

    data = [["ID", "Name", "Email", "Department", "Position", "Status"]]
    for emp in queryset[:100]:
        data.append([
            emp.employee_id, emp.full_name, emp.email,
            emp.department.name, emp.position.title,
            emp.get_employment_status_display(),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
    ]))
    elements.append(table)
    doc.build(elements)

    log_activity(request, "export", f"Exported employees to PDF", "Employee")
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="employees_{datetime.now():%Y%m%d}.pdf"'
    return response


@login_required
def employee_print_view(request):
    queryset = _get_employee_queryset(request)
    return render(request, "employees/print.html", {"employees": queryset})


@login_required
def positions_by_department_ajax(request, department_id):
    positions = Position.objects.filter(department_id=department_id, is_active=True)
    return JsonResponse({"positions": [{"id": p.pk, "title": p.title} for p in positions]})


@hr_manager_required
def announcement_list_view(request):
    announcements = CompanyAnnouncement.objects.select_related("created_by").all()
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        announcement = form.save(commit=False)
        announcement.created_by = request.user
        announcement.save()
        from notifications.models import Notification
        from notifications.utils import notify_all_users

        notify_all_users(
            title="New Announcement",
            message=announcement.title,
            notification_type=Notification.Type.ANNOUNCEMENT,
            link=reverse("dashboard:home"),
        )
        log_activity(request, "create", f"Announcement: {announcement.title}", "CompanyAnnouncement", announcement.pk)
        messages.success(request, "Announcement created successfully.")
        return redirect("employees:announcements")

    return render(request, "employees/announcements.html", {
        "announcements": announcements,
        "form": form,
    })


@hr_manager_required
def audit_log_view(request):
    """Global audit trail browser for HR managers and admins."""
    logs = ActivityLog.objects.select_related("user").all()
    action = request.GET.get("action", "")
    model_name = request.GET.get("model", "")
    q = request.GET.get("q", "")

    if action:
        logs = logs.filter(action=action)
    if model_name:
        logs = logs.filter(model_name=model_name)
    if q:
        logs = logs.filter(
            Q(description__icontains=q)
            | Q(object_repr__icontains=q)
            | Q(user__username__icontains=q)
        )

    model_names = (
        ActivityLog.objects.exclude(model_name="")
        .values_list("model_name", flat=True)
        .distinct()
        .order_by("model_name")
    )

    return render(request, "employees/audit_log.html", {
        "logs": logs[:200],
        "action": action,
        "model_name": model_name,
        "q": q,
        "model_names": model_names,
        "action_choices": ActivityLog.Action.choices,
    })


@login_required
def recognition_wall_view(request):
    """Company-wide employee recognition wall."""
    from django.utils import timezone

    base_qs = EmployeeRecognition.objects.select_related(
        "employee", "employee__department", "awarded_by"
    )
    recognitions = base_qs[:50]
    today = timezone.localdate()
    month_start = today.replace(day=1)

    return render(request, "employees/recognition_wall.html", {
        "recognitions": recognitions,
        "recognition_total": base_qs.count(),
        "recognition_employees": base_qs.values("employee_id").distinct().count(),
        "recognition_recent": base_qs.filter(awarded_date__gte=month_start).count(),
    })


@hr_manager_required
@require_POST
def employee_timeline_add(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = TimelineEventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.employee = employee
        event.created_by = request.user
        event.save()
        log_activity(request, "create", f"Timeline: {event.title}", "EmployeeTimelineEvent", event.pk)
        messages.success(request, "Timeline event added.")
        return redirect("employees:detail", pk=pk)
    return redirect("employees:detail", pk=pk)


@hr_manager_required
@require_POST
def employee_recognition_add(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = RecognitionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        rec = form.save(commit=False)
        rec.employee = employee
        rec.awarded_by = request.user
        rec.save()
        log_activity(request, "create", f"Recognition: {rec.title}", "EmployeeRecognition", rec.pk)
        messages.success(request, "Recognition added.")
        return redirect("employees:detail", pk=pk)
    return redirect("employees:detail", pk=pk)
