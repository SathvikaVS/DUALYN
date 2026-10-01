from django import forms
from .models import Resume


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file']

def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['file'].widget.attrs.update({'class': 'form-control'})