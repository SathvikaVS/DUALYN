from django import forms
from .models import StudentProfile


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
<<<<<<< HEAD
        fields = [
            'Full_name', 'Education', 'College', 'Carrer_Interest',
            'Status', 'Year_of_Study', 'Years_of_Experience',
        ]
=======
        fields = ['college', 'degree', 'graduation_year', 'career_interest']
>>>>>>> 0eccc4aa234a062197f4f76ac7222cc14d5e2894
