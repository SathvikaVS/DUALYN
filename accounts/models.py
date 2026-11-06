from django.conf import settings
from django.db import models


class UserRole(models.Model):
    STUDENT = 'student'
    COMPANY = 'company'
    PROFESSOR = 'professor'
    ADMIN = 'admin'
    ROLE_CHOICES = [
        (STUDENT, 'Student'),
        (COMPANY, 'Company / employer'),
        (PROFESSOR, 'Professor / researcher'),
        (ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='role_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=STUDENT)
    organization = models.CharField(max_length=150, blank=True)
    is_verified = models.BooleanField(default=False, help_text='Tick after you have checked that this company/professor is genuine.')

    def __str__(self):
        return f'{self.user} ({self.role})'

    @property
    def is_collaborator(self):
        return self.role in (self.COMPANY, self.PROFESSOR)