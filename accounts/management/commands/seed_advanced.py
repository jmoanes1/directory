"""Seed skills, leave types, and sample advanced module data."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from attendance.models import LeaveType
from employees.models import (
    Employee, EmployeeRecognition, EmployeeSkill,
    EmployeeTimelineEvent, Skill,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Seed skills, leave types, and advanced module sample data"

    def handle(self, *args, **options):
        # Leave types
        leave_types = [
            ("Annual Leave", "AL", 20, True, "#2563eb"),
            ("Sick Leave", "SL", 10, True, "#dc2626"),
            ("Personal Leave", "PL", 5, False, "#d97706"),
            ("Maternity/Paternity", "MP", 90, True, "#9333ea"),
        ]
        for name, code, max_days, is_paid, color in leave_types:
            LeaveType.objects.get_or_create(
                code=code,
                defaults={"name": name, "max_days_per_year": max_days, "is_paid": is_paid, "color": color},
            )

        # Skills catalog
        skills_data = [
            ("Python", "technical"), ("JavaScript", "technical"), ("Django", "technical"),
            ("Project Management", "soft"), ("Communication", "soft"), ("Leadership", "soft"),
            ("English", "language"), ("Spanish", "language"),
            ("AWS Certified", "certification"), ("PMP", "certification"),
        ]
        skills = {}
        for name, category in skills_data:
            skill, _ = Skill.objects.get_or_create(name=name, defaults={"category": category})
            skills[name] = skill

        # Assign skills to employees
        assignments = [
            ("john.doe@company.com", "Python", "4"), ("john.doe@company.com", "Django", "3"),
            ("sarah.smith@company.com", "Python", "4"), ("sarah.smith@company.com", "JavaScript", "3"),
            ("sarah.smith@company.com", "Leadership", "3"),
            ("emily.j@company.com", "Communication", "4"), ("emily.j@company.com", "Project Management", "3"),
            ("michael.b@company.com", "Communication", "3"), ("michael.b@company.com", "English", "4"),
            ("lisa.w@company.com", "Project Management", "2"),
        ]
        for email, skill_name, proficiency in assignments:
            emp = Employee.objects.filter(email=email).first()
            if emp and skill_name in skills:
                EmployeeSkill.objects.get_or_create(
                    employee=emp,
                    skill=skills[skill_name],
                    defaults={"proficiency": proficiency},
                )

        # Link HR user to employee profile for attendance
        hr_user = User.objects.filter(username="hr_manager").first()
        emily = Employee.objects.filter(email="emily.j@company.com").first()
        if hr_user and emily and not emily.user_id:
            emily.user = hr_user
            emily.save(update_fields=["user"])

        # Social links on sample employees
        john = Employee.objects.filter(email="john.doe@company.com").first()
        if john:
            john.linkedin_url = "https://linkedin.com/in/johndoe"
            john.github_url = "https://github.com/johndoe"
            john.save(update_fields=["linkedin_url", "github_url"])

        sarah = Employee.objects.filter(email="sarah.smith@company.com").first()
        if sarah:
            sarah.linkedin_url = "https://linkedin.com/in/sarahsmith"
            sarah.save(update_fields=["linkedin_url"])

        # Career timeline events
        today = date.today()
        timeline_data = [
            (john, "hire", "Joined Engineering", "Started as Software Engineer", john.date_hired if john else today),
            (john, "promotion", "Promoted to Senior Engineer", "Outstanding performance review", today.replace(year=today.year - 1)),
            (sarah, "hire", "Joined Engineering", "Senior Developer role", sarah.date_hired if sarah else today),
            (emily, "transfer", "Moved to Human Resources", "Internal transfer from Operations", today.replace(year=today.year - 2)),
        ]
        for emp, etype, title, desc, edate in timeline_data:
            if emp:
                EmployeeTimelineEvent.objects.get_or_create(
                    employee=emp, title=title, event_date=edate,
                    defaults={"event_type": etype, "description": desc},
                )

        # Recognition awards
        recognition_data = [
            (john, "Employee of the Month", "excellence", "Exceptional delivery on Q4 project"),
            (sarah, "Innovation Award", "innovation", "Led migration to new architecture"),
            (emily, "Team Player Award", "teamwork", "Supported onboarding for 5 new hires"),
        ]
        for emp, title, cat, desc in recognition_data:
            if emp:
                EmployeeRecognition.objects.get_or_create(
                    employee=emp, title=title, awarded_date=today,
                    defaults={"category": cat, "description": desc},
                )

        self.stdout.write(self.style.SUCCESS("Advanced module data seeded successfully!"))
