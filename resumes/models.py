from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import os


def validate_resume_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.pdf', '.docx']:
        raise ValidationError('Only PDF and DOCX files are allowed.')


class Resume(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to='resumes/%Y/%m/', validators=[validate_resume_file])
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.file.name}"

    class Meta:
        ordering = ['-uploaded_at']
