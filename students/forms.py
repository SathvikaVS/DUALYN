from django import forms
from .models import Student_Profile


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student_Profile
        fields = [
            'Full_name', 'Education', 'College', 'Carrer_Interest',
            'Status', 'Year_of_Study', 'Years_of_Experience',
        ]