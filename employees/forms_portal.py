"""HR forms for timeline and recognition."""

from django import forms

from accounts.forms import StyledFormMixin
from employees.models import EmployeeRecognition, EmployeeTimelineEvent


class TimelineEventForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeTimelineEvent
        fields = ["event_type", "title", "description", "event_date"]
        widgets = {"event_date": forms.DateInput(attrs={"type": "date"})}


class RecognitionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeRecognition
        fields = ["title", "description", "category", "awarded_date"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "awarded_date": forms.DateInput(attrs={"type": "date"}),
        }
