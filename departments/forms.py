"""Department forms."""

from django import forms

from accounts.forms import StyledFormMixin
from departments.models import Department
from employees.models import Employee


class DepartmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "head", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["head"].queryset = Employee.objects.filter(is_active=True).order_by("last_name")
        self.fields["code"].required = False
