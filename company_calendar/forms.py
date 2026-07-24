"""Forms for company calendar management."""

from django import forms

from accounts.forms import StyledFormMixin
from company_calendar.models import CalendarEntry


class CalendarEntryForm(StyledFormMixin, forms.ModelForm):
    """Create and edit calendar entries."""

    class Meta:
        model = CalendarEntry
        fields = ["title", "date", "event_type", "description", "is_active"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs.setdefault("placeholder", "Event or holiday title")
        self.fields["description"].widget.attrs.setdefault(
            "placeholder", "Optional details for employees"
        )
