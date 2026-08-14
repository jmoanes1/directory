"""Create default super admin and sample data."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from departments.models import Department
from employees.models import CompanyAnnouncement, Employee
from positions.models import Position

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with default admin user and sample data"

    def handle(self, *args, **options):
        if User.objects.filter(username="admin").exists():
            admin = User.objects.get(username="admin")
            self.stdout.write(self.style.WARNING("Admin user already exists."))
        else:
            admin = User.objects.create_superuser(
                username="admin",
                email="admin@company.com",
                password="Admin@12345",
                first_name="Super",
                last_name="Admin",
                role=User.Role.SUPER_ADMIN,
                is_registration_approved=True,
            )
            self.stdout.write("  Admin: admin / Admin@12345")

        if User.objects.filter(username="hr_manager").exists():
            self.stdout.write(self.style.WARNING("HR manager already exists."))
        else:
            User.objects.create_user(
                username="hr_manager",
                email="hr@company.com",
                password="Hr@12345",
                first_name="Jane",
                last_name="HR",
                role=User.Role.HR_MANAGER,
                is_registration_approved=True,
            )
            self.stdout.write("  HR Manager: hr_manager / Hr@12345")

        if Department.objects.exists():
            self.stdout.write(self.style.WARNING("Sample departments already exist. Skipping org seed."))
            return

        # Departments
        engineering = Department.objects.create(name="Engineering", description="Software development team")
        hr_dept = Department.objects.create(name="Human Resources", description="People operations")
        marketing = Department.objects.create(name="Marketing", description="Brand and growth")
        finance = Department.objects.create(name="Finance", description="Financial operations")

        # Positions
        positions_data = [
            ("Software Engineer", engineering),
            ("Senior Developer", engineering),
            ("HR Specialist", hr_dept),
            ("Marketing Manager", marketing),
            ("Accountant", finance),
        ]
        positions = {}
        for title, dept in positions_data:
            positions[title] = Position.objects.create(title=title, department=dept)

        # Sample employees
        employees_data = [
            ("John", "Michael", "Doe", "john.doe@company.com", engineering, "Software Engineer"),
            ("Sarah", "", "Smith", "sarah.smith@company.com", engineering, "Senior Developer"),
            ("Emily", "Rose", "Johnson", "emily.j@company.com", hr_dept, "HR Specialist"),
            ("Michael", "", "Brown", "michael.b@company.com", marketing, "Marketing Manager"),
            ("Lisa", "Ann", "Wilson", "lisa.w@company.com", finance, "Accountant"),
        ]

        manager = None
        for i, (first, middle, last, email, dept, pos_title) in enumerate(employees_data):
            emp = Employee.objects.create(
                first_name=first,
                middle_name=middle,
                last_name=last,
                email=email,
                phone_number=f"+1-555-010{i}",
                date_of_birth=date(1990 + i, (i % 12) + 1, (i * 3 % 28) + 1),
                gender=Employee.Gender.MALE if i % 2 == 0 else Employee.Gender.FEMALE,
                address=f"{100 + i} Main Street, City, State",
                date_hired=date.today() - timedelta(days=365 * (i + 1)),
                department=dept,
                position=positions[pos_title],
                manager=manager if i > 0 and dept == engineering else None,
                employment_status=Employee.EmploymentStatus.ACTIVE,
                emergency_contact=f"Emergency Contact {i + 1}",
                bio=f"Experienced professional in {dept.name}.",
            )
            if i == 0:
                manager = emp

        engineering.head = manager
        engineering.save()

        CompanyAnnouncement.objects.create(
            title="Welcome to Employee Directory",
            content="Welcome to our new Employee Directory system. Explore features and manage your profile.",
            created_by=admin,
        )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
        self.stdout.write("  Admin: admin / Admin@12345")
        self.stdout.write("  HR Manager: hr_manager / Hr@12345")
