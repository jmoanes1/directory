"""Administrator-only employee account management views."""

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.forms import CustomPasswordChangeForm
from accounts.forms_employee_accounts import EmployeeAccountCreateForm, EmployeeAccountEditForm
from accounts.permissions import employee_account_admin_required
from accounts.services_employee_accounts import (
    create_employee_account,
    reset_employee_password,
    send_credentials_email,
    update_employee_account,
)
from accounts.services_user_accounts import (
    delete_user_account,
    set_user_active,
    validate_user_account_action,
)
from departments.models import Department
from employees.models import Employee
from employees.utils import log_activity
from positions.models import Position


def permission_denied_view(request, exception=None):
    """Custom 403 access denied page."""
    return render(
        request,
        "accounts/403.html",
        {"message": str(exception) if exception else None},
        status=403,
    )


@login_required
def force_password_change_view(request):
    """Require password change before continuing."""
    if not request.user.must_change_password:
        return redirect("dashboard:home")

    form = CustomPasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.must_change_password = False
        user.save(update_fields=["must_change_password"])
        update_session_auth_hash(request, user)
        log_activity(request, "update", "Completed required password change", "User", user.pk, user.username)
        messages.success(request, "Password updated. You can now use the application.")
        return redirect("dashboard:home")

    return render(request, "accounts/force_password_change.html", {"form": form})


@employee_account_admin_required
def employee_account_list_view(request):
    """Searchable list of employee accounts (admin only)."""
    qs = (
        Employee.objects.select_related("department", "position", "user")
        .filter(user__isnull=False)
        .order_by("-created_at")
    )

    search = request.GET.get("q", "").strip()
    department = request.GET.get("department", "")
    position = request.GET.get("position", "")
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(email__icontains=search)
            | Q(employee_id__icontains=search)
            | Q(user__username__icontains=search)
        )
    if department:
        qs = qs.filter(department_id=department)
    if position:
        qs = qs.filter(position_id=position)
    if role:
        qs = qs.filter(user__role=role)
    if status == "active":
        qs = qs.filter(user__is_active=True, is_active=True)
    elif status == "inactive":
        qs = qs.filter(Q(user__is_active=False) | Q(is_active=False))

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/employee_accounts/list.html",
        {
            "page_obj": page_obj,
            "departments": Department.objects.order_by("name"),
            "positions": Position.objects.filter(is_active=True).order_by("title"),
            "search": search,
            "selected_department": department,
            "selected_position": position,
            "selected_role": role,
            "selected_status": status,
        },
    )


@employee_account_admin_required
def employee_account_create_view(request):
    """Create employee record + login account in one step."""
    prefill_employee = None
    emp_pk = request.GET.get("employee")
    if emp_pk:
        prefill_employee = get_object_or_404(Employee, pk=emp_pk, user__isnull=True)

    form = EmployeeAccountCreateForm(
        request.POST or None,
        request.FILES or None,
        employee=prefill_employee,
        actor=request.user,
    )
    if request.method == "POST" and form.is_valid():
        data = form._normalized_data()
        data["temporary_password"] = form.cleaned_data["temporary_password"]
        employee, user, password = create_employee_account(
            form_data=data,
            profile_photo=form.cleaned_data.get("profile_photo"),
            created_by=request.user,
            existing_employee=prefill_employee,
        )
        log_activity(
            request,
            "create",
            f"Created employee account {employee.full_name} (@{user.username})",
            "Employee",
            employee.pk,
            employee.full_name,
        )
        request.session["new_account_credentials"] = {
            "employee_id": employee.employee_id,
            "employee_pk": employee.pk,
            "full_name": employee.full_name,
            "username": user.username,
            "password": password,
            "email": employee.email,
        }
        return redirect("accounts:employee_account_created")

    return render(
        request,
        "accounts/employee_accounts/form.html",
        {
            "form": form,
            "title": "Add Employee Account" if not prefill_employee else f"Add Account — {prefill_employee.full_name}",
            "is_create": True,
            "employee": prefill_employee,
        },
    )


@employee_account_admin_required
def employee_account_created_view(request):
    """Success screen with copyable credentials."""
    creds = request.session.pop("new_account_credentials", None)
    if not creds:
        return redirect("accounts:employee_account_list")
    employee = get_object_or_404(Employee, pk=creds["employee_pk"])
    return render(
        request,
        "accounts/employee_accounts/created.html",
        {"creds": creds, "employee": employee},
    )


@employee_account_admin_required
def employee_account_detail_view(request, pk):
    employee = get_object_or_404(
        Employee.objects.select_related("department", "position", "user", "manager"),
        pk=pk,
    )
    if not employee.user_id:
        messages.warning(request, "This employee has no login account yet.")
        return redirect("accounts:employee_account_create")

    return render(
        request,
        "accounts/employee_accounts/detail.html",
        {"employee": employee},
    )


@employee_account_admin_required
def employee_account_edit_view(request, pk):
    employee = get_object_or_404(Employee.objects.select_related("user"), pk=pk)
    if not employee.user_id:
        messages.error(request, "No account linked to this employee.")
        return redirect("accounts:employee_account_list")

    if employee.user.is_super_admin and not request.user.is_super_admin:
        messages.error(request, "Only a Super Admin can edit administrator accounts.")
        return redirect("accounts:employee_account_detail", pk=employee.pk)

    form = EmployeeAccountEditForm(
        request.POST or None,
        request.FILES or None,
        employee=employee,
        actor=request.user,
    )
    if request.method == "POST" and form.is_valid():
        data = form._normalized_data()
        update_employee_account(
            employee=employee,
            form_data=data,
            profile_photo=form.cleaned_data.get("profile_photo"),
            new_password=form.cleaned_data.get("new_password") or None,
        )
        log_activity(
            request,
            "update",
            f"Updated employee account {employee.full_name}",
            "Employee",
            employee.pk,
            employee.full_name,
        )
        messages.success(request, f"Account for {employee.full_name} updated successfully.")
        return redirect("accounts:employee_account_detail", pk=employee.pk)

    return render(
        request,
        "accounts/employee_accounts/form.html",
        {
            "form": form,
            "title": f"Edit — {employee.full_name}",
            "is_create": False,
            "employee": employee,
        },
    )


@employee_account_admin_required
@require_POST
def employee_account_reset_password_view(request, pk):
    employee = get_object_or_404(Employee.objects.select_related("user"), pk=pk)
    if not employee.user_id:
        messages.error(request, "No account linked to this employee.")
        return redirect("accounts:employee_account_list")

    password = reset_employee_password(employee)
    log_activity(
        request,
        "update",
        f"Reset password for {employee.full_name}",
        "User",
        employee.user_id,
        employee.user.username,
    )
    request.session["new_account_credentials"] = {
        "employee_id": employee.employee_id,
        "employee_pk": employee.pk,
        "full_name": employee.full_name,
        "username": employee.user.username,
        "password": password,
        "email": employee.email,
        "reset": True,
    }
    return redirect("accounts:employee_account_created")


@employee_account_admin_required
@require_POST
def employee_account_toggle_active_view(request, pk):
    employee = get_object_or_404(Employee.objects.select_related("user"), pk=pk)
    if not employee.user_id:
        messages.error(request, "No account linked to this employee.")
        return redirect("accounts:employee_account_list")

    user = employee.user
    active = not user.is_active
    action = "deactivate" if not active else "activate"

    try:
        if not active:
            validate_user_account_action(actor=request.user, target=user, action="deactivate")
        set_user_active(target_user=user, active=active)
    except PermissionDenied as exc:
        messages.error(request, str(exc))
        next_url = request.POST.get("next") or reverse("accounts:employee_account_list")
        return redirect(next_url)

    log_activity(
        request,
        "update",
        f"{action.title()}d account for {employee.full_name}",
        "Employee",
        employee.pk,
        employee.full_name,
    )
    messages.success(
        request,
        f"Account for {employee.full_name} is now {'active' if active else 'inactive'}.",
    )
    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("accounts:employee_account_detail", pk=employee.pk)


@employee_account_admin_required
@require_POST
def employee_account_delete_view(request, pk):
    employee = get_object_or_404(Employee.objects.select_related("user"), pk=pk)
    if not employee.user_id:
        messages.error(request, "No account linked to this employee.")
        return redirect("accounts:employee_account_list")

    name = employee.full_name
    user = employee.user
    username = user.username

    try:
        validate_user_account_action(actor=request.user, target=user, action="delete")
        delete_user_account(user)
    except PermissionDenied as exc:
        messages.error(request, str(exc))
        return redirect("accounts:employee_account_list")

    log_activity(
        request,
        "delete",
        f"Deleted employee account {name} (@{username})",
        "Employee",
        pk,
        name,
    )
    messages.success(request, f"Employee account for {name} has been deleted.")
    return redirect("accounts:employee_account_list")


@employee_account_admin_required
@require_POST
def employee_account_send_credentials_view(request, pk):
    employee = get_object_or_404(Employee.objects.select_related("user"), pk=pk)
    creds = request.session.get("new_account_credentials")
    if not creds or creds.get("employee_pk") != employee.pk:
        messages.error(request, "No credentials available to send. Reset the password first.")
        return redirect("accounts:employee_account_detail", pk=employee.pk)

    try:
        send_credentials_email(
            employee=employee,
            username=creds["username"],
            password=creds["password"],
            requested_by=request.user,
            login_url=request.build_absolute_uri("/accounts/login/"),
        )
        log_activity(
            request,
            "update",
            f"Emailed credentials to {employee.full_name}",
            "Employee",
            employee.pk,
            employee.full_name,
        )
        messages.success(request, f"Login credentials sent to {employee.email}.")
    except Exception:
        messages.error(request, "Could not send email. Check email server settings.")
    return redirect("accounts:employee_account_detail", pk=employee.pk)
