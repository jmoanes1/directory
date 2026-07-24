"""Forms for skills, org chart filters, and AI search."""

from django import forms

from accounts.forms import StyledFormMixin
from employees.models import EmployeeSkill, Skill


class SkillForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "category", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class EmployeeSkillForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeSkill
        fields = ["employee", "skill", "proficiency", "years_experience", "notes"]


class AISearchForm(StyledFormMixin, forms.Form):
    query = forms.CharField(
        label="Ask anything about employees",
        widget=forms.TextInput(attrs={
            "placeholder": 'e.g. "Find engineers in Marketing" or "Who reports to John?"',
            "autocomplete": "off",
            "id": "aiSearchInput",
        }),
    )
