import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from jobs.models import JobRole
from skills.models import Skill


class SkillAnalysis(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)
    readiness_score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    scoring_breakdown = models.JSONField(default=dict, blank=True)
    has_warning = models.BooleanField(default=False)
    warning_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} → {self.job_role.title} ({self.readiness_score}%)"


class SkillGap(models.Model):
    STATUS_CHOICES = [
        ('demonstrated', 'Demonstrated'),
        ('covered', 'Demonstrated'),
        ('needs_improvement', 'Needs Improvement'),
        ('mentioned', 'Mentioned / Basic'),
        ('missing', 'Missing from Resume'),
        ('not_assessed', 'Not Assessed'),
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
    evidence_sources = models.JSONField(default=list, blank=True)
    required_level = models.CharField(max_length=50, default='Intermediate', blank=True)
    gap_explanation = models.TextField(blank=True)
    recommended_step = models.TextField(blank=True)

    def __str__(self):
        return f"{self.skill.name}: {self.status} ({self.priority})"


def generate_share_token() -> str:
    return secrets.token_urlsafe(32)


class ShareLink(models.Model):
    analysis = models.ForeignKey(SkillAnalysis, on_delete=models.CASCADE, related_name='share_links')
    token = models.CharField(max_length=64, unique=True, db_index=True, default=generate_share_token)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    hide_name = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    def __str__(self):
        status = "revoked" if self.is_revoked else ("expired" if self.is_expired else "active")
        return f"ShareLink({self.analysis_id}, {self.token[:8]}..., {status})"
