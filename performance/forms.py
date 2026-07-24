"""Performance management forms."""

from django import forms

from accounts.forms import StyledFormMixin
from performance.models import EmployeeGoal, PerformanceReview


class PerformanceReviewForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PerformanceReview
        fields = [
            "employee", "review_period", "period_start", "period_end",
            "overall_rating", "strengths", "areas_for_improvement",
            "goals_summary", "manager_feedback", "status",
        ]
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "strengths": forms.Textarea(attrs={"rows": 3}),
            "areas_for_improvement": forms.Textarea(attrs={"rows": 3}),
            "goals_summary": forms.Textarea(attrs={"rows": 3}),
            "manager_feedback": forms.Textarea(attrs={"rows": 3}),
        }


class EmployeeGoalForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeGoal
        fields = ["employee", "title", "description", "target_date", "progress", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "target_date": forms.DateInput(attrs={"type": "date"}),
        }
