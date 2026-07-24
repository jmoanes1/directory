"""Attendance and leave request tests."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from attendance.models import LeaveRequest, LeaveType
from attendance.services import sync_employee_leave_status, sync_leave_employment_statuses
from departments.models import Department
from employees.models import Employee
from positions.models import Position

User = get_user_model()


class LeaveRequestViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.leave_type = LeaveType.objects.create(
            name="Annual Leave",
            code="AL",
            max_days_per_year=15,
        )
        dept = Department.objects.create(name="Engineering")
        position = Position.objects.create(title="Developer", department=dept)

        self.admin = User.objects.create_superuser(
            username="test_admin",
            email="admin@test.com",
            password="Admin@12345",
            role=User.Role.SUPER_ADMIN,
        )
        self.employee_user = User.objects.create_user(
            username="test_employee",
            email="employee@test.com",
            password="Employee@12345",
            role=User.Role.EMPLOYEE,
        )
        self.target_employee = Employee.objects.create(
            user=self.employee_user,
            first_name="Test",
            last_name="Employee",
            email="employee@test.com",
            department=dept,
            position=position,
            date_hired=date.today(),
        )

    def test_admin_must_select_employee(self):
        """Admin without a linked profile must pick an employee on the form."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("attendance:leave_request"),
            {
                "leave_type": self.leave_type.pk,
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=1)).isoformat(),
                "reason": "Vacation",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LeaveRequest.objects.filter(reason="Vacation").exists())

    def test_admin_can_submit_for_selected_employee(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("attendance:leave_request"),
            {
                "employee": self.target_employee.pk,
                "leave_type": self.leave_type.pk,
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=1)).isoformat(),
                "reason": "Vacation",
            },
        )
        self.assertEqual(response.status_code, 302)
        leave = LeaveRequest.objects.get(reason="Vacation")
        self.assertEqual(leave.employee_id, self.target_employee.pk)

    def test_employee_submits_for_self(self):
        self.client.force_login(self.employee_user)
        response = self.client.post(
            reverse("attendance:leave_request"),
            {
                "leave_type": self.leave_type.pk,
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=2)).isoformat(),
                "reason": "Personal",
            },
        )
        self.assertEqual(response.status_code, 302)
        leave = LeaveRequest.objects.get(reason="Personal")
        self.assertEqual(leave.employee.user_id, self.employee_user.pk)


class LeaveStatusSyncTests(TestCase):
    """On Leave must clear after the approved leave end date."""

    def setUp(self):
        dept = Department.objects.create(name="Ops")
        position = Position.objects.create(title="Analyst", department=dept)
        self.employee = Employee.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@test.com",
            department=dept,
            position=position,
            date_hired=date.today() - timedelta(days=30),
            employment_status=Employee.EmploymentStatus.ON_LEAVE,
            availability_status=Employee.AvailabilityStatus.ON_LEAVE,
        )
        self.leave_type = LeaveType.objects.create(name="Sick", code="SL", max_days_per_year=10)

    def test_expired_leave_restores_active_status(self):
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=1),
            reason="Past leave",
            status=LeaveRequest.Status.APPROVED,
        )
        sync_leave_employment_statuses(date.today())
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.employment_status, Employee.EmploymentStatus.ACTIVE)
        self.assertEqual(self.employee.availability_status, Employee.AvailabilityStatus.AVAILABLE)

    def test_active_leave_keeps_on_leave_status(self):
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
            reason="Current leave",
            status=LeaveRequest.Status.APPROVED,
        )
        sync_leave_employment_statuses(date.today())
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.employment_status, Employee.EmploymentStatus.ON_LEAVE)

    def test_future_approved_leave_does_not_mark_on_leave_yet(self):
        self.employee.employment_status = Employee.EmploymentStatus.ACTIVE
        self.employee.availability_status = Employee.AvailabilityStatus.AVAILABLE
        self.employee.save(update_fields=["employment_status", "availability_status"])
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=5),
            reason="Upcoming leave",
            status=LeaveRequest.Status.APPROVED,
        )
        sync_employee_leave_status(self.employee, date.today())
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.employment_status, Employee.EmploymentStatus.ACTIVE)
