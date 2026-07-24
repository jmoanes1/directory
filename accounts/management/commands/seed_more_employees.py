"""Add 20 more sample employees to the directory."""

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from departments.models import Department
from employees.models import Employee
from positions.models import Position


class Command(BaseCommand):
    help = "Seed 20 additional employees (skips emails that already exist)"

    def handle(self, *args, **options):
        departments = {
            dept.name: dept
            for dept in Department.objects.filter(is_active=True)
        }
        if not departments:
            self.stdout.write(self.style.ERROR("No departments found. Run seed_data first."))
            return

        positions_by_title = {
            pos.title: pos
            for pos in Position.objects.filter(is_active=True).select_related("department")
        }
        if not positions_by_title:
            self.stdout.write(self.style.ERROR("No positions found. Run seed_data first."))
            return

        engineering = departments.get("Engineering") or next(iter(departments.values()))
        hr_dept = departments.get("Human Resources") or engineering
        marketing = departments.get("Marketing") or engineering
        finance = departments.get("Finance") or engineering

        def pos(title, fallback_dept):
            if title in positions_by_title:
                return positions_by_title[title]
            return Position.objects.filter(department=fallback_dept, is_active=True).first()

        manager = Employee.objects.filter(department=engineering).order_by("date_hired").first()

        employees_data = [
            ("Daniel", "James", "Martinez", "daniel.martinez@company.com", engineering, "Software Engineer"),
            ("Olivia", "Grace", "Anderson", "olivia.anderson@company.com", engineering, "Senior Developer"),
            ("Ethan", "Paul", "Thomas", "ethan.thomas@company.com", engineering, "Software Engineer"),
            ("Sophia", "Marie", "Jackson", "sophia.jackson@company.com", engineering, "Senior Developer"),
            ("Noah", "Lee", "White", "noah.white@company.com", engineering, "Software Engineer"),
            ("Ava", "", "Harris", "ava.harris@company.com", engineering, "Software Engineer"),
            ("Liam", "Scott", "Clark", "liam.clark@company.com", engineering, "Senior Developer"),
            ("Mia", "Rose", "Lewis", "mia.lewis@company.com", hr_dept, "HR Specialist"),
            ("William", "", "Walker", "william.walker@company.com", hr_dept, "HR Specialist"),
            ("Isabella", "Jane", "Hall", "isabella.hall@company.com", hr_dept, "HR Specialist"),
            ("James", "Robert", "Allen", "james.allen@company.com", marketing, "Marketing Manager"),
            ("Charlotte", "Elise", "Young", "charlotte.young@company.com", marketing, "Marketing Manager"),
            ("Benjamin", "", "King", "benjamin.king@company.com", marketing, "Marketing Manager"),
            ("Amelia", "Kate", "Wright", "amelia.wright@company.com", marketing, "Marketing Manager"),
            ("Lucas", "David", "Lopez", "lucas.lopez@company.com", finance, "Accountant"),
            ("Harper", "", "Hill", "harper.hill@company.com", finance, "Accountant"),
            ("Henry", "Alan", "Green", "henry.green@company.com", finance, "Accountant"),
            ("Evelyn", "May", "Adams", "evelyn.adams@company.com", finance, "Accountant"),
            ("Alexander", "Ray", "Baker", "alexander.baker@company.com", engineering, "Software Engineer"),
            ("Scarlett", "Ivy", "Nelson", "scarlett.nelson@company.com", engineering, "Senior Developer"),
        ]

        created_count = 0
        skipped_count = 0

        for i, (first, middle, last, email, dept, pos_title) in enumerate(employees_data):
            if Employee.objects.filter(email__iexact=email).exists():
                skipped_count += 1
                continue

            position = pos(pos_title, dept)
            if not position:
                self.stdout.write(self.style.WARNING(f"No position for {email}; skipping."))
                skipped_count += 1
                continue

            Employee.objects.create(
                first_name=first,
                middle_name=middle,
                last_name=last,
                email=email,
                phone_number=f"+1-555-02{i:02d}",
                date_of_birth=date(1988 + (i % 8), (i % 12) + 1, ((i * 5) % 27) + 1),
                gender=Employee.Gender.MALE if i % 2 == 0 else Employee.Gender.FEMALE,
                address=f"{200 + i} Oak Avenue, Suite {i + 1}, Metro City",
                date_hired=date.today() - timedelta(days=90 + (i * 45)),
                department=dept,
                position=position,
                manager=manager if dept == engineering and manager else None,
                employment_status=Employee.EmploymentStatus.ACTIVE,
                work_location=Employee.WorkLocation.HYBRID if i % 3 == 0 else Employee.WorkLocation.OFFICE,
                emergency_contact_name=f"{first} Emergency Contact",
                emergency_contact=f"+1-555-09{i:02d}",
                bio=f"Dedicated {pos_title.lower()} contributing to {dept.name}.",
            )
            created_count += 1
            self.stdout.write(f"  Added: {first} {last} ({email})")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created_count} employee(s), skipped {skipped_count} existing."
        ))
