from django import forms
from .models import StudentSkill, Skill


class StudentSkillForm(forms.ModelForm):
    class Meta:
        model = StudentSkill
        fields = ['skill', 'level']