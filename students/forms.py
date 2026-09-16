from django import forms
from .models import StudentProfile


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['college', 'degree', 'graduation_year', 'career_interest']