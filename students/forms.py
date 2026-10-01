from django import forms
from .models import Student_Profile


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student_Profile
        fields = [
            'Full_name', 'Education', 'College', 'Carrer_Interest',
            'Status', 'Year_of_Study', 'Years_of_Experience',
        ]

def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    for name, field in self.fields.items():
        existing = field.widget.attrs.get('class', '')
        css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        field.widget.attrs['class'] = (existing + ' ' + css_class).strip()