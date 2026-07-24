"""Seed recruitment and performance sample data."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from departments.models import Department
from employees.models import Employee
from performance.models import EmployeeGoal, PerformanceReview
from positions.models import Position
from recruitment.models import Application, Candidate, Interview, JobOpening

User = get_user_model()


class Command(BaseCommand):
    help = "Seed recruitment pipeline and performance review sample data"

    def handle(self, *args, **options):
        hr_user = User.objects.filter(username="hr_manager").first()
        eng_dept = Department.objects.filter(name__icontains="Engineering").first()
        hr_dept = Department.objects.filter(name__icontains="Human").first()
        if not eng_dept:
            eng_dept = Department.objects.first()
        if not hr_dept:
            hr_dept = Department.objects.first()

        dev_pos = Position.objects.filter(title__icontains="Developer").first()
        hr_pos = Position.objects.filter(title__icontains="HR").first()

        jobs_data = [
            {
                "title": "Senior Python Developer",
                "department": eng_dept,
                "position": dev_pos,
                "description": "Join our engineering team to build scalable Django applications.",
                "requirements": "5+ years Python, Django, REST APIs, PostgreSQL/SQLite experience.",
                "location": "Remote",
                "status": JobOpening.Status.OPEN,
            },
            {
                "title": "HR Coordinator",
                "department": hr_dept,
                "position": hr_pos,
                "description": "Support recruitment, onboarding, and employee engagement initiatives.",
                "requirements": "2+ years HR experience, strong communication skills.",
                "location": "New York, NY",
                "status": JobOpening.Status.OPEN,
            },
            {
                "title": "Frontend Engineer",
                "department": eng_dept,
                "description": "Build modern, accessible UI with vanilla JS and Django templates.",
                "requirements": "JavaScript, CSS, HTML, responsive design.",
                "location": "Hybrid",
                "status": JobOpening.Status.CLOSED,
            },
        ]

        jobs = []
        for data in jobs_data:
            job, created = JobOpening.objects.get_or_create(
                title=data["title"],
                defaults={
                    **data,
                    "posted_by": hr_user,
                    "employment_type": JobOpening.EmploymentType.FULL_TIME,
                    "salary_range": "$80,000 – $120,000",
                },
            )
            jobs.append(job)
            if created:
                self.stdout.write(f"  Created job: {job.title}")

        candidates_data = [
            ("Alex", "Rivera", "alex.rivera@email.com", "applied"),
            ("Jordan", "Kim", "jordan.kim@email.com", "screening"),
            ("Taylor", "Morgan", "taylor.morgan@email.com", "interview"),
            ("Casey", "Brooks", "casey.brooks@email.com", "offer"),
            ("Riley", "Chen", "riley.chen@email.com", "rejected"),
        ]

        status_map = {
            "applied": Application.Status.APPLIED,
            "screening": Application.Status.SCREENING,
            "interview": Application.Status.INTERVIEW,
            "offer": Application.Status.OFFER,
            "rejected": Application.Status.REJECTED,
        }

        senior_job = jobs[0] if jobs else None
        if senior_job:
            for first, last, email, stage in candidates_data:
                candidate, _ = Candidate.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": first,
                        "last_name": last,
                        "phone": "555-0100",
                        "source": "Company Website",
                    },
                )
                Application.objects.get_or_create(
                    job=senior_job,
                    candidate=candidate,
                    defaults={
                        "status": status_map[stage],
                        "cover_letter": f"I am excited to apply for the {senior_job.title} role.",
                        "reviewed_by": hr_user,
                    },
                )

            interview_app = Application.objects.filter(
                job=senior_job, status=Application.Status.INTERVIEW
            ).first()
            if interview_app and not interview_app.interviews.exists():
                Interview.objects.create(
                    application=interview_app,
                    scheduled_at=timezone.now() + timedelta(days=3),
                    interview_type=Interview.Type.VIDEO,
                    location_or_link="https://meet.example.com/interview",
                    interviewer=hr_user,
                    status=Interview.Status.SCHEDULED,
                )

        # Performance reviews and goals
        employees = Employee.objects.filter(is_active=True)[:4]
        today = date.today()
        for i, emp in enumerate(employees):
            PerformanceReview.objects.get_or_create(
                employee=emp,
                review_period="Q1 2026",
                defaults={
                    "reviewer": hr_user,
                    "period_start": date(today.year, 1, 1),
                    "period_end": date(today.year, 3, 31),
                    "overall_rating": 4 if i % 2 == 0 else 3,
                    "strengths": "Strong teamwork and consistent delivery.",
                    "areas_for_improvement": "Continue developing leadership skills.",
                    "manager_feedback": "Great contributor to the team.",
                    "status": PerformanceReview.Status.SUBMITTED,
                },
            )
            EmployeeGoal.objects.get_or_create(
                employee=emp,
                title="Complete professional development course",
                defaults={
                    "description": "Finish an online course relevant to role.",
                    "target_date": today + timedelta(days=90),
                    "progress": 25 + (i * 15),
                    "status": EmployeeGoal.Status.IN_PROGRESS,
                    "created_by": hr_user,
                },
            )

        self.stdout.write(self.style.SUCCESS("Recruitment & performance seed data created."))
