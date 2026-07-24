"""Performance management views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import hr_manager_required
from employees.models import Employee
from employees.utils import log_activity
from performance.forms import EmployeeGoalForm, PerformanceReviewForm
from performance.models import EmployeeGoal, PerformanceReview


def _get_employee(user):
    return getattr(user, "employee_profile", None)


@login_required
def performance_dashboard(request):
    employee = _get_employee(request.user)
    can_manage = request.user.can_manage_employees()

    if can_manage:
        reviews = PerformanceReview.objects.select_related("employee", "reviewer")[:10]
        goals = EmployeeGoal.objects.select_related("employee").filter(status=EmployeeGoal.Status.IN_PROGRESS)[:10]
        avg_rating = PerformanceReview.objects.filter(status=PerformanceReview.Status.SUBMITTED).aggregate(
            avg=Avg("overall_rating")
        )["avg"]
        stats = {
            "total_reviews": PerformanceReview.objects.count(),
            "active_goals": EmployeeGoal.objects.filter(status=EmployeeGoal.Status.IN_PROGRESS).count(),
            "avg_rating": round(avg_rating, 1) if avg_rating else "—",
            "employees": Employee.objects.filter(is_active=True).count(),
        }
    elif employee:
        reviews = PerformanceReview.objects.filter(employee=employee).select_related("reviewer")
        goals = EmployeeGoal.objects.filter(employee=employee)
        stats = None
    else:
        reviews = PerformanceReview.objects.none()
        goals = EmployeeGoal.objects.none()
        stats = None

    return render(request, "performance/dashboard.html", {
        "reviews": reviews,
        "goals": goals,
        "stats": stats,
        "employee": employee,
        "can_manage": can_manage,
    })


@hr_manager_required
def review_create_view(request):
    form = PerformanceReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.reviewer = request.user
        review.save()
        log_activity(request, "create", f"Performance review: {review.employee.full_name}", "PerformanceReview", review.pk)
        messages.success(request, "Performance review created.")
        return redirect("performance:dashboard")
    return render(request, "performance/review_form.html", {"form": form, "title": "New Performance Review"})


@login_required
def review_detail_view(request, pk):
    review = get_object_or_404(
        PerformanceReview.objects.select_related("employee", "reviewer"), pk=pk
    )
    employee = _get_employee(request.user)
    if not request.user.can_manage_employees() and (not employee or employee.pk != review.employee_id):
        messages.error(request, "Permission denied.")
        return redirect("performance:dashboard")
    return render(request, "performance/review_detail.html", {"review": review})


@login_required
def goal_list_view(request):
    employee = _get_employee(request.user)
    if request.user.can_manage_employees():
        goals = EmployeeGoal.objects.select_related("employee", "created_by")
    elif employee:
        goals = EmployeeGoal.objects.filter(employee=employee).select_related("created_by")
    else:
        goals = EmployeeGoal.objects.none()
    return render(request, "performance/goal_list.html", {"goals": goals, "can_manage": request.user.can_manage_employees()})


@login_required
def goal_create_view(request):
    employee = _get_employee(request.user)
    if not request.user.can_manage_employees() and not employee:
        messages.error(request, "No employee profile linked.")
        return redirect("performance:dashboard")

    form = EmployeeGoalForm(request.POST or None)
    if not request.user.can_manage_employees():
        if "employee" in form.fields:
            del form.fields["employee"]

    if request.method == "POST" and form.is_valid():
        goal = form.save(commit=False)
        goal.created_by = request.user
        if not request.user.can_manage_employees():
            goal.employee = employee
        goal.save()
        messages.success(request, "Goal created.")
        return redirect("performance:goals")
    return render(request, "performance/goal_form.html", {"form": form, "title": "New Goal", "can_manage": request.user.can_manage_employees()})
