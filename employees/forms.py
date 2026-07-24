"""Employee and announcement forms."""

from django import forms
from django.core.exceptions import ValidationError

from accounts.forms import StyledFormMixin
from employees.models import CompanyAnnouncement, Employee
from positions.models import Position


EMPLOYEE_FIELD_PLACEHOLDERS = {
    "first_name": "First name",
    "middle_name": "Middle name",
    "last_name": "Last name",
    "suffix": "Suffix (e.g. Jr., Sr.)",
    "email": "Email address",
    "phone_number": "Contact number",
    "address": "Home address",
    "bio": "Short professional bio",
    "emergency_contact": "Primary emergency contact",
    "emergency_contact_name": "Contact name",
    "emergency_contact_phone": "Contact phone number",
    "emergency_contact_relationship": "Relationship (e.g. Spouse, Parent)",
    "linkedin_url": "https://linkedin.com/in/username",
    "github_url": "https://github.com/username",
    "twitter_url": "https://twitter.com/username",
    "website_url": "https://example.com",
}


class EmployeeForm(StyledFormMixin, forms.ModelForm):
    """Form for creating and editing employee records."""

    class Meta:
        model = Employee
        fields = [
            "first_name", "middle_name", "last_name", "suffix", "email", "phone_number",
            "date_of_birth", "gender", "address", "date_hired", "department",
            "position", "manager", "employment_status", "employee_type", "work_location",
            "availability_status", "profile_photo",
            "emergency_contact", "emergency_contact_name",
            "emergency_contact_phone", "emergency_contact_relationship", "bio",
            "linkedin_url", "github_url", "twitter_url", "website_url",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "date_hired": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "bio": forms.Textarea(attrs={"rows": 4}),
            "profile_photo": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, placeholder in EMPLOYEE_FIELD_PLACEHOLDERS.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs["placeholder"] = placeholder

        self.fields["manager"].queryset = Employee.objects.filter(is_active=True).order_by("last_name")
        if self.instance and self.instance.pk:
            self.fields["manager"].queryset = self.fields["manager"].queryset.exclude(pk=self.instance.pk)

        department_id = None
        if self.data.get("department"):
            department_id = self.data.get("department")
        elif self.instance and self.instance.department_id:
            department_id = self.instance.department_id

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

    def clean(self):
        cleaned = super().clean()
        department = cleaned.get("department")
        position = cleaned.get("position")
        if department and position and position.department_id != department.pk:
            self.add_error("position", "Position must belong to the selected department.")
        return cleaned

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size") and photo.size > 5 * 1024 * 1024:
            raise ValidationError("Profile photo must be under 5 MB.")
        return photo


class AnnouncementForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CompanyAnnouncement
        fields = ["title", "content", "is_active"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 5}),
        }
