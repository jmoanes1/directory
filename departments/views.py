"""Department views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import department_manager_required
from departments.forms import DepartmentForm
from departments.models import Department
from employees.utils import log_activity


@login_required
def department_list_view(request):
    departments = Department.objects.select_related("head").all()
    return render(request, "departments/list.html", {
        "departments": departments,
        "can_manage": request.user.can_manage_departments(),
    })


@department_manager_required
def department_create_view(request):
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        department = form.save()
        log_activity(request, "create", f"Created department {department.name}", "Department", department.pk, department.name)
        messages.success(request, f"Department {department.name} created successfully.")
        return redirect("departments:list")

    return render(request, "departments/form.html", {"form": form, "title": "Create Department"})


@department_manager_required
def department_edit_view(request, pk):
    department = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == "POST" and form.is_valid():
        department = form.save()
        log_activity(request, "update", f"Updated department {department.name}", "Department", department.pk, department.name)
        messages.success(request, f"Department {department.name} updated successfully.")
        return redirect("departments:list")

    return render(request, "departments/form.html", {
        "form": form, "department": department, "title": "Edit Department",
    })


@department_manager_required
@require_POST
def department_delete_view(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if department.employees.exists():
        messages.error(request, "Cannot delete department with assigned employees.")
        return redirect("departments:list")

    name = department.name
    dept_id = department.pk
    department.delete()
    log_activity(request, "delete", f"Deleted department {name}", "Department", dept_id, name)
    messages.success(request, f"Department {name} deleted successfully.")
    return redirect("departments:list")
