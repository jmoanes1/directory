"""Administrator forms for unified employee + account management."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.forms import StyledFormMixin
from accounts.services_employee_accounts import (
    ACCOUNT_ROLE_CHOICES,
    HR_ASSIGNABLE_ROLES,
    generate_temporary_password,
)
from departments.models import Department
from employees.models import Employee
from positions.models import Position

User = get_user_model()

PERSONAL_FIELD_PLACEHOLDERS = {
    "first_name": "First name",
    "middle_name": "Middle name",
    "last_name": "Last name",
    "suffix": "Suffix (e.g. Jr., Sr.)",
    "phone_number": "Contact number",
    "email": "Email address",
    "address": "Home address",
}

ACCOUNT_FIELD_PLACEHOLDERS = {
    "username": "Username",
    "temporary_password": "Temporary password",
    "new_password": "New temporary password",
}


class EmployeeAccountBaseForm(StyledFormMixin, forms.Form):
    """Shared fields for creating and editing employee accounts."""

    # Personal information
    first_name = forms.CharField(max_length=100)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100)
    suffix = forms.CharField(max_length=20, required=False, label="Suffix")
    gender = forms.ChoiceField(
        choices=[("", "---------")] + list(Employee.Gender.choices),
        required=False,
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    phone_number = forms.CharField(max_length=20, required=False, label="Contact number")
    email = forms.EmailField(label="Email address")
    address = forms.CharField(
        required=False,
        label="Home address",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    profile_photo = forms.ImageField(required=False)

    # Employment information
    department = forms.ModelChoiceField(queryset=Department.objects.all().order_by("name"))
    position = forms.ModelChoiceField(queryset=Position.objects.none())
    employment_status = forms.ChoiceField(choices=Employee.EmploymentStatus.choices)
    employee_type = forms.ChoiceField(choices=Employee.EmployeeType.choices, label="Employee type")
    date_hired = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    # Account information
    username = forms.CharField(max_length=150)
    account_role = forms.ChoiceField(choices=ACCOUNT_ROLE_CHOICES, label="Role")
    account_active = forms.ChoiceField(
        choices=(("1", "Active"), ("0", "Inactive")),
        label="Account status",
    )

    def __init__(self, *args, employee=None, actor=None, **kwargs):
        self.employee = employee
        self.actor = actor
        super().__init__(*args, **kwargs)

        for field_name, placeholder in PERSONAL_FIELD_PLACEHOLDERS.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["placeholder"] = placeholder

        for field_name, placeholder in ACCOUNT_FIELD_PLACEHOLDERS.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["placeholder"] = placeholder

        # HR Managers can assign Employee or HR Manager roles only.
        if self.actor and not self.actor.is_super_admin:
            allowed = {role for role in HR_ASSIGNABLE_ROLES}
            self.fields["account_role"].choices = [
                choice for choice in ACCOUNT_ROLE_CHOICES if choice[0] in allowed
            ]

        department_id = self.data.get("department") or (
            employee.department_id if employee else None
        )
        if department_id:
            self.fields["position"].queryset = Position.objects.filter(
                department_id=department_id, is_active=True
            )
        else:
            self.fields["position"].queryset = Position.objects.filter(is_active=True)

        submitted_position = self.data.get("position")
        if submitted_position:
            self.fields["position"].queryset = (
                self.fields["position"].queryset | Position.objects.filter(pk=submitted_position)
            )

        if employee and employee.user_id:
            user = employee.user
            self.fields["username"].initial = user.username
            self.fields["account_role"].initial = user.role
            self.fields["account_active"].initial = "1" if user.is_active else "0"
            self.fields["first_name"].initial = employee.first_name
            self.fields["middle_name"].initial = employee.middle_name
            self.fields["last_name"].initial = employee.last_name
            self.fields["suffix"].initial = employee.suffix
            self.fields["gender"].initial = employee.gender
            self.fields["date_of_birth"].initial = employee.date_of_birth
            self.fields["phone_number"].initial = employee.phone_number
            self.fields["email"].initial = employee.email
            self.fields["address"].initial = employee.address
            self.fields["department"].initial = employee.department_id
            self.fields["position"].initial = employee.position_id
            self.fields["employment_status"].initial = employee.employment_status
            self.fields["employee_type"].initial = employee.employee_type
            self.fields["date_hired"].initial = employee.date_hired

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size") and photo.size > 5 * 1024 * 1024:
            raise ValidationError("Profile photo must be under 5 MB.")
        return photo

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username__iexact=username)
        if self.employee and self.employee.user_id:
            qs = qs.exclude(pk=self.employee.user_id)
        if qs.exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = User.objects.filter(email__iexact=email)
        if self.employee and self.employee.user_id:
            qs = qs.exclude(pk=self.employee.user_id)
        if qs.exists():
            raise ValidationError("This email is already registered to another account.")
        qs_emp = Employee.objects.filter(email__iexact=email)
        if self.employee:
            qs_emp = qs_emp.exclude(pk=self.employee.pk)
        if qs_emp.exists():
            raise ValidationError("This email is already used by another employee record.")
        return email

    def clean_account_role(self):
        role = self.cleaned_data["account_role"]
        if self.actor and not self.actor.is_super_admin and role == User.Role.SUPER_ADMIN:
            raise ValidationError("Only a Super Admin can assign the Administrator role.")
        if (
            self.employee
            and self.employee.user_id
            and self.employee.user.is_super_admin
            and self.actor
            and not self.actor.is_super_admin
        ):
            raise ValidationError("Only a Super Admin can change an administrator account.")
        return role

    def _normalized_data(self):
        cleaned = self.cleaned_data
        return {
            "first_name": cleaned["first_name"],
            "middle_name": cleaned.get("middle_name", ""),
            "last_name": cleaned["last_name"],
            "suffix": cleaned.get("suffix", ""),
            "gender": cleaned.get("gender", ""),
            "date_of_birth": cleaned.get("date_of_birth"),
            "phone_number": cleaned.get("phone_number", ""),
            "email": cleaned["email"],
            "address": cleaned.get("address", ""),
            "department": cleaned["department"],
            "position": cleaned["position"],
            "employment_status": cleaned["employment_status"],
            "employee_type": cleaned["employee_type"],
            "date_hired": cleaned["date_hired"],
            "username": cleaned["username"],
            "account_role": cleaned["account_role"],
            "account_active": cleaned["account_active"] == "1",
        }


class EmployeeAccountCreateForm(EmployeeAccountBaseForm):
    generate_password = forms.BooleanField(
        required=False,
        initial=True,
        label="Generate temporary password automatically",
    )
    temporary_password = forms.CharField(
        required=False,
        label="Temporary password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Leave blank when auto-generate is enabled.",
    )

    def clean(self):
        cleaned = super().clean()
        generate = cleaned.get("generate_password")
        password = cleaned.get("temporary_password")
        if not generate and not password:
            raise ValidationError(
                {"temporary_password": "Enter a temporary password or enable auto-generate."}
            )
        if generate and not password:
            cleaned["temporary_password"] = generate_temporary_password()
        return cleaned


class EmployeeAccountEditForm(EmployeeAccountBaseForm):
    new_password = forms.CharField(
        required=False,
        label="New temporary password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Optional. Employee will be required to change it on next login.",
    )

    def clean(self):
        cleaned = super().clean()
        if not self.employee or not self.employee.user_id:
            raise ValidationError("This employee does not have a linked account.")
        return cleaned
