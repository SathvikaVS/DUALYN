from django import forms
from .models import StudentProfile


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'Full_name', 'Education', 'College', 'Carrer_Interest',
            'Status', 'Year_of_Study', 'Years_of_Experience',
        ]