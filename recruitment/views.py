"""Recruitment views — jobs, pipeline, interviews, onboarding."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import hr_manager_required
from employees.utils import log_activity
from recruitment.forms import (
    ApplicationForm,
    ApplicationStatusForm,
    InterviewForm,
    JobOpeningForm,
    OnboardingTaskForm,
)
from recruitment.models import Application, Candidate, Interview, JobOpening, OnboardingTask

DEFAULT_ONBOARDING_TASKS = [
    ("Complete HR paperwork", "Sign employment contract and tax forms", 1),
    ("IT setup", "Laptop, email account, and system access", 2),
    ("Department orientation", "Meet the team and tour the office", 3),
    ("Policy training", "Complete compliance and security training", 4),
    ("30-day check-in", "Manager follow-up meeting", 5),
]


@login_required
def job_list_view(request):
    if request.user.can_manage_employees():
        jobs = JobOpening.objects.select_related("department", "position", "posted_by").annotate(
            app_count=Count("applications")
        )
    else:
        jobs = JobOpening.objects.filter(status=JobOpening.Status.OPEN).select_related("department", "position")
    return render(request, "recruitment/job_list.html", {
        "jobs": jobs,
        "can_manage": request.user.can_manage_employees(),
    })


@login_required
def job_detail_view(request, pk):
    job = get_object_or_404(JobOpening.objects.select_related("department", "position"), pk=pk)
    if job.status != JobOpening.Status.OPEN and not request.user.can_manage_employees():
        messages.error(request, "This job is no longer accepting applications.")
        return redirect("recruitment:job_list")
    return render(request, "recruitment/job_detail.html", {
        "job": job,
        "can_manage": request.user.can_manage_employees(),
    })


@hr_manager_required
def job_create_view(request):
    form = JobOpeningForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.posted_by = request.user
        job.save()
        log_activity(request, "create", f"Job opening: {job.title}", "JobOpening", job.pk)
        messages.success(request, "Job opening created.")
        return redirect("recruitment:job_detail", pk=job.pk)
    return render(request, "recruitment/job_form.html", {"form": form, "title": "Post Job Opening"})


@hr_manager_required
def job_edit_view(request, pk):
    job = get_object_or_404(JobOpening, pk=pk)
    form = JobOpeningForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job opening updated.")
        return redirect("recruitment:job_detail", pk=pk)
    return render(request, "recruitment/job_form.html", {"form": form, "title": "Edit Job Opening", "job": job})


@login_required
def job_apply_view(request, pk):
    job = get_object_or_404(JobOpening, pk=pk, status=JobOpening.Status.OPEN)
    form = ApplicationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        candidate, _ = Candidate.objects.update_or_create(
            email=form.cleaned_data["email"],
            defaults={
                "first_name": form.cleaned_data["first_name"],
                "last_name": form.cleaned_data["last_name"],
                "phone": form.cleaned_data.get("phone", ""),
                "linkedin_url": form.cleaned_data.get("linkedin_url", ""),
                "source": form.cleaned_data.get("source", ""),
            },
        )
        if form.cleaned_data.get("resume"):
            candidate.resume = form.cleaned_data["resume"]
            candidate.save(update_fields=["resume"])

        if Application.objects.filter(job=job, candidate=candidate).exists():
            messages.warning(request, "You have already applied for this position.")
            return redirect("recruitment:job_detail", pk=pk)

        application = Application.objects.create(
            job=job,
            candidate=candidate,
            cover_letter=form.cleaned_data.get("cover_letter", ""),
        )
        log_activity(request, "create", f"Application: {candidate.full_name} → {job.title}", "Application", application.pk)
        messages.success(request, "Application submitted successfully! We'll be in touch.")
        return redirect("recruitment:job_list")

    return render(request, "recruitment/apply.html", {"job": job, "form": form})


@hr_manager_required
def pipeline_view(request):
    """Hiring pipeline kanban grouped by application status."""
    applications = Application.objects.select_related(
        "job", "candidate", "reviewed_by"
    ).order_by("-applied_at")
    columns = {status.value: [] for status in Application.Status}
    for app in applications:
        columns[app.status].append(app)
    status_columns = [
        {"key": choice[0], "label": choice[1], "apps": columns[choice[0]]}
        for choice in Application.Status.choices
    ]
    stats = {
        "total": applications.count(),
        "open_jobs": JobOpening.objects.filter(status=JobOpening.Status.OPEN).count(),
        "interviews": Interview.objects.filter(status=Interview.Status.SCHEDULED).count(),
    }
    return render(request, "recruitment/pipeline.html", {
        "status_columns": status_columns,
        "stats": stats,
    })


@hr_manager_required
def application_detail_view(request, pk):
    application = get_object_or_404(
        Application.objects.select_related("job", "candidate", "reviewed_by"),
        pk=pk,
    )
    status_form = ApplicationStatusForm(request.POST or None, instance=application)
    interview_form = InterviewForm(request.POST or None)
    task_form = OnboardingTaskForm(request.POST or None)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "status" and status_form.is_valid():
            app = status_form.save(commit=False)
            app.reviewed_by = request.user
            app.save()
            if app.status == Application.Status.HIRED and not app.onboarding_tasks.exists():
                for title, desc, order in DEFAULT_ONBOARDING_TASKS:
                    OnboardingTask.objects.create(
                        application=app, title=title, description=desc, sort_order=order
                    )
            messages.success(request, "Application status updated.")
            return redirect("recruitment:application_detail", pk=pk)
        if action == "interview" and interview_form.is_valid():
            interview = interview_form.save(commit=False)
            interview.application = application
            if not interview.interviewer_id:
                interview.interviewer = request.user
            interview.save()
            application.status = Application.Status.INTERVIEW
            application.save(update_fields=["status", "updated_at"])
            messages.success(request, "Interview scheduled.")
            return redirect("recruitment:application_detail", pk=pk)
        if action == "task" and task_form.is_valid():
            task = task_form.save(commit=False)
            task.application = application
            task.save()
            messages.success(request, "Onboarding task added.")
            return redirect("recruitment:application_detail", pk=pk)

    return render(request, "recruitment/application_detail.html", {
        "application": application,
        "status_form": status_form,
        "interview_form": interview_form,
        "task_form": task_form,
        "interviews": application.interviews.select_related("interviewer"),
        "tasks": application.onboarding_tasks.all(),
    })


@hr_manager_required
@require_POST
def onboarding_task_toggle(request, pk):
    task = get_object_or_404(OnboardingTask, pk=pk)
    task.is_completed = not task.is_completed
    task.save(update_fields=["is_completed"])
    return redirect("recruitment:application_detail", pk=task.application_id)


@login_required
def resume_download_view(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    if not request.user.can_manage_employees():
        messages.error(request, "Permission denied.")
        return redirect("recruitment:job_list")
    if not candidate.resume:
        messages.error(request, "No resume on file.")
        return redirect("recruitment:pipeline")
    return FileResponse(
        candidate.resume.open("rb"),
        as_attachment=True,
        filename=candidate.resume.name.split("/")[-1],
    )
