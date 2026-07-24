"""Employee self-service portal and manager dashboard."""

from datetime import date

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from attendance.models import AttendanceRecord, LeaveRequest
from attendance.services import get_leave_balances, sync_leave_employment_statuses
from employees.models import Employee, EmployeeDocument, EmployeeRecognition
from employees.utils import log_activity
from portal.forms import EmployeeDocumentUploadForm, SelfServiceProfileForm


def _get_employee(user):
    return getattr(user, "employee_profile", None)


def _require_employee(view_func):
    """Redirect users without a linked employee profile."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        employee = _get_employee(request.user)
        if not employee and not request.user.can_manage_employees():
            messages.error(request, "No employee profile linked to your account.")
            return redirect("dashboard:home")
        return view_func(request, *args, **kwargs)
    return wrapper


@_require_employee
def self_service_home(request):
    employee = _get_employee(request.user)
    today = date.today()

    today_attendance = None
    recent_leaves = []
    leave_balances = []
    documents_count = 0

    if employee:
        today_attendance = AttendanceRecord.objects.filter(employee=employee, date=today).first()
        recent_leaves = LeaveRequest.objects.filter(employee=employee).select_related("leave_type")[:5]
        leave_balances = get_leave_balances(employee)
        documents_count = employee.documents.count()

    return render(request, "portal/self_service.html", {
        "employee": employee,
        "today_attendance": today_attendance,
        "recent_leaves": recent_leaves,
        "leave_balances": leave_balances,
        "documents_count": documents_count,
        "profile_completion": employee.profile_completion if employee else 0,
    })


@_require_employee
def self_service_profile(request):
    employee = _get_employee(request.user)
    if not employee:
        return redirect("dashboard:home")

    form = SelfServiceProfileForm(request.POST or None, instance=employee)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request, "update", "Updated personal profile via self-service", "Employee", employee.pk)
        messages.success(request, "Profile updated successfully.")
        return redirect("portal:profile")

    return render(request, "portal/profile_edit.html", {
        "employee": employee,
        "form": form,
        "profile_completion": employee.profile_completion,
    })


@_require_employee
def self_service_documents(request):
    employee = _get_employee(request.user)
    if not employee:
        return redirect("dashboard:home")

    form = EmployeeDocumentUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        doc = form.save(commit=False)
        doc.employee = employee
        doc.uploaded_by = request.user
        doc.save()
        log_activity(request, "create", f"Uploaded document: {doc.title}", "EmployeeDocument", doc.pk)
        messages.success(request, "Document uploaded successfully.")
        return redirect("portal:documents")

    documents = employee.documents.all()
    return render(request, "portal/documents.html", {
        "employee": employee,
        "documents": documents,
        "form": form,
    })


@login_required
def document_download(request, pk):
    """Secure document download — owner, manager, or HR."""
    doc = get_object_or_404(EmployeeDocument, pk=pk)
    employee = _get_employee(request.user)
    is_owner = employee and employee.pk == doc.employee_id
    is_hr = request.user.can_manage_employees()
    is_manager = employee and doc.employee.manager_id == employee.pk

    if not (is_owner or is_hr or is_manager):
        messages.error(request, "Permission denied.")
        return redirect("dashboard:home")

    from django.http import FileResponse
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.file.name.split("/")[-1])


@login_required
@require_POST
def document_delete(request, pk):
    doc = get_object_or_404(EmployeeDocument, pk=pk)
    employee = _get_employee(request.user)
    if not (employee and employee.pk == doc.employee_id) and not request.user.can_manage_employees():
        messages.error(request, "Permission denied.")
        return redirect("portal:documents")

    title = doc.title
    doc.file.delete(save=False)
    doc.delete()
    log_activity(request, "delete", f"Deleted document: {title}", "EmployeeDocument", pk)
    messages.success(request, "Document deleted.")
    return redirect("portal:documents")


@login_required
def manager_dashboard(request):
    """Dashboard for managers — team stats, pending leave, direct reports."""
    employee = _get_employee(request.user)
    if not employee and not request.user.can_manage_employees():
        messages.error(request, "Manager profile required.")
        return redirect("dashboard:home")

    # Hide On Leave after the approved leave end date
    sync_leave_employment_statuses()

    if request.user.can_manage_employees() and not employee:
        direct_reports = Employee.objects.filter(is_active=True).select_related("department", "position")[:20]
        team_size = Employee.objects.filter(is_active=True).count()
    elif employee:
        direct_reports = employee.direct_reports.filter(is_active=True).select_related("department", "position")
        team_size = direct_reports.count()
    else:
        direct_reports = Employee.objects.none()
        team_size = 0

    report_ids = list(direct_reports.values_list("pk", flat=True))
    pending_leaves = LeaveRequest.objects.filter(
        employee_id__in=report_ids,
        status=LeaveRequest.Status.PENDING,
    ).select_related("employee", "leave_type")[:10]

    today = date.today()
    on_leave = Employee.objects.filter(
        pk__in=report_ids,
        leave_requests__status=LeaveRequest.Status.APPROVED,
        leave_requests__start_date__lte=today,
        leave_requests__end_date__gte=today,
    ).distinct()[:10]

    present_today = AttendanceRecord.objects.filter(
        employee_id__in=report_ids,
        date=today,
        status=AttendanceRecord.Status.PRESENT,
    ).count()

    dept_breakdown = (
        Employee.objects.filter(pk__in=report_ids, is_active=True)
        .values("department__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    ) if report_ids else []

    return render(request, "portal/manager_dashboard.html", {
        "employee": employee,
        "team_size": team_size,
        "direct_reports": direct_reports,
        "pending_leaves": pending_leaves,
        "on_leave": on_leave,
        "present_today": present_today,
        "dept_breakdown": dept_breakdown,
        "is_hr_view": request.user.can_manage_employees() and not employee,
    })
