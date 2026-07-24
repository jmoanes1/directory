"""Recruitment forms."""

from django import forms
from django.core.exceptions import ValidationError

from accounts.forms import StyledFormMixin
from recruitment.models import Application, Candidate, Interview, JobOpening, OnboardingTask


class JobOpeningForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = JobOpening
        fields = [
            "title", "department", "position", "description", "requirements",
            "location", "employment_type", "salary_range", "status",
            "opens_at", "closes_at",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
            "opens_at": forms.DateInput(attrs={"type": "date"}),
            "closes_at": forms.DateInput(attrs={"type": "date"}),
        }


class ApplicationForm(StyledFormMixin, forms.ModelForm):
    """Public / internal job application."""

    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    linkedin_url = forms.URLField(required=False)
    source = forms.CharField(max_length=100, required=False, initial="Company Website")
    resume = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={"accept": ".pdf,.doc,.docx"}),
    )

    class Meta:
        model = Application
        fields = ["cover_letter"]
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell us why you're a great fit..."})}

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and hasattr(resume, "size") and resume.size > 10 * 1024 * 1024:
            raise ValidationError("Resume must be under 10 MB.")
        return resume


class ApplicationStatusForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Application
        fields = ["status", "hr_notes"]
        widgets = {"hr_notes": forms.Textarea(attrs={"rows": 3})}


class InterviewForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Interview
        fields = ["scheduled_at", "interview_type", "location_or_link", "interviewer", "notes", "status"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class OnboardingTaskForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = OnboardingTask
        fields = ["title", "description", "due_date", "sort_order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
