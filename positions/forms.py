"""Position forms."""

from django import forms

from accounts.forms import StyledFormMixin
from positions.models import Position


class PositionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Position
        fields = ["title", "department", "description", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
