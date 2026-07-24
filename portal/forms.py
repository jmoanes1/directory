"""Self-service and portal forms."""

from django import forms
from django.core.exceptions import ValidationError

from accounts.forms import StyledFormMixin
from employees.models import Employee, EmployeeDocument


class SelfServiceProfileForm(StyledFormMixin, forms.ModelForm):
    """Fields employees may update on their own profile."""

    class Meta:
        model = Employee
        fields = [
            "phone_number", "address", "bio",
            "emergency_contact", "emergency_contact_name",
            "emergency_contact_phone", "emergency_contact_relationship",
            "work_location", "availability_status",
            "linkedin_url", "github_url", "twitter_url", "website_url",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "bio": forms.Textarea(attrs={"rows": 4}),
        }


class EmployeeDocumentUploadForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeDocument
        fields = ["document_type", "title", "file", "is_confidential"]
        widgets = {
            "file": forms.FileInput(attrs={
                "accept": ".pdf,.doc,.docx,.jpg,.jpeg,.png,.webp",
            }),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file and hasattr(file, "size") and file.size > 10 * 1024 * 1024:
            raise ValidationError("File must be under 10 MB.")
        return file
