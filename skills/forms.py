from django import forms
from .models import StudentSkill, Skill


class StudentSkillForm(forms.ModelForm):
    class Meta:
        model = StudentSkill
        fields = ['skill', 'level']


def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['skill'].widget.attrs.update({'class': 'form-select'})
    self.fields['level'].widget.attrs.update({'class': 'form-select'})