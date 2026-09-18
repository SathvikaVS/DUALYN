from django.db import models
from django.conf import settings
from jobs.models import JobRole
from skills.models import Skill


class SkillAnalysis(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)
    readiness_score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} → {self.job_role.title} ({self.readiness_score}%)"


class SkillGap(models.Model):
    STATUS_CHOICES = [
        ('covered', 'Covered'),
        ('needs_improvement', 'Needs Improvement'),
        ('missing', 'Missing'),
    ]
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    analysis = models.ForeignKey(SkillAnalysis, on_delete=models.CASCADE, related_name='gaps')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    reasoning = models.TextField(blank=True)

    def __str__(self):
        return f"{self.skill.name}: {self.status} ({self.priority})"
