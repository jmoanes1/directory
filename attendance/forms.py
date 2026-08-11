"""Attendance and leave management forms."""

from django import forms
from django.core.exceptions import ValidationError

from accounts.forms import StyledFormMixin
from attendance.models import AttendanceRecord, LeaveRequest, LeaveType
from attendance.services import get_leave_balances
from employees.models import Employee


class LeaveRequestForm(StyledFormMixin, forms.ModelForm):
    """Leave request form — self-service for employees, picker for HR/admin."""

    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True).order_by("last_name", "first_name"),
        required=False,
        label="Employee",
        help_text="Choose who this leave request is for.",
    )

    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason"]
        labels = {
            "leave_type": "Leave type",
            "start_date": "Start date",
            "end_date": "End date",
            "reason": "Reason",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Briefly describe why you need time off (optional)",
            }),
        }

    def __init__(self, *args, user=None, linked_employee=None, **kwargs):
        self.user = user
        self.linked_employee = linked_employee
        super().__init__(*args, **kwargs)

        if user and user.can_manage_employees():
            self.fields["employee"].required = True
            self.fields["employee"].queryset = Employee.objects.filter(is_active=True).order_by(
                "last_name", "first_name"
            )
            if linked_employee:
                self.fields["employee"].initial = linked_employee.pk
            # Managers see employee first so the flow reads naturally.
            self.order_fields(["employee", "leave_type", "start_date", "end_date", "reason"])
        else:
            self.fields.pop("employee", None)

        if linked_employee:
            self._apply_leave_type_balance_labels(linked_employee)

    def _apply_leave_type_balance_labels(self, employee):
        """Show remaining days beside each leave type in the dropdown."""
        balances = {row["leave_type"].pk: row for row in get_leave_balances(employee)}
        choices = [("", "---------")]
        for leave_type in LeaveType.objects.filter(is_active=True):
            balance = balances.get(leave_type.pk)
            if balance is not None:
                label = f"{leave_type.name} ({balance['remaining']} days left)"
            else:
                label = leave_type.name
            choices.append((leave_type.pk, label))
        self.fields["leave_type"].choices = choices

    def clean(self):
        cleaned_data = super().clean()

        if self.user and self.user.can_manage_employees():
            if not cleaned_data.get("employee"):
                raise ValidationError("Select an employee for this leave request.")
        elif not self.linked_employee:
            raise ValidationError("No employee profile is linked to your account.")

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

        return cleaned_data


class LeaveReviewForm(StyledFormMixin, forms.Form):
    action = forms.ChoiceField(choices=[("approved", "Approve"), ("rejected", "Reject")])
    review_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional notes"}),
    )


class AttendanceCheckForm(StyledFormMixin, forms.Form):
    notes = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={"placeholder": "Optional notes"}))


class LeaveTypeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ["name", "code", "max_days_per_year", "is_paid", "color", "is_active"]
