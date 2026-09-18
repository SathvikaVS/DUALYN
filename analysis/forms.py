from django import forms
from jobs.models import JobRole


class RunAnalysisForm(forms.Form):
    job_role = forms.ModelChoiceField(queryset=JobRole.objects.all(), label="Target Job")