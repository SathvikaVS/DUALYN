from django.db import models

from django.db import models
from skills.models import Skill


class JobRole(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']


class JobSkill(models.Model):
    IMPORTANCE_CHOICES = [
        (1, '1 - Nice to have'),
        (2, '2 - Useful'),
        (3, '3 - Important'),
        (4, '4 - Very Important'),
        (5, '5 - Critical'),
    ]

    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name='job_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    importance_weight = models.PositiveSmallIntegerField(choices=IMPORTANCE_CHOICES, default=3)
    is_fundamental = models.BooleanField(default=False)

    class Meta:
        unique_together = ('job_role', 'skill')
        ordering = ['-importance_weight']

    def __str__(self):
        return f"{self.job_role.title} → {self.skill.name} (weight {self.importance_weight})"
