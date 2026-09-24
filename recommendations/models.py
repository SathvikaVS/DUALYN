from django.db import models
from analysis.models import SkillAnalysis, SkillGap


class Recommendation(models.Model):
    analysis = models.ForeignKey(SkillAnalysis, on_delete=models.CASCADE, related_name='recommendations')
    skill_gap = models.ForeignKey(SkillGap, on_delete=models.CASCADE, related_name='recommendations')
    steps = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation for {self.skill_gap.skill.name}"


class LearningRoadmap(models.Model):
    analysis = models.OneToOneField(SkillAnalysis, on_delete=models.CASCADE, related_name='roadmap')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Roadmap for {self.analysis}"


class RoadmapItem(models.Model):
    PHASE_CHOICES = [
        (1, 'Phase 1 - Strengthen Fundamentals'),
        (2, 'Phase 2 - Core Skills'),
        (3, 'Phase 3 - Advanced Skills'),
        (4, 'Phase 4 - Portfolio Project'),
    ]

    roadmap = models.ForeignKey(LearningRoadmap, on_delete=models.CASCADE, related_name='items')
    skill_gap = models.ForeignKey(SkillGap, on_delete=models.CASCADE)
    phase = models.PositiveSmallIntegerField(choices=PHASE_CHOICES)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['phase', 'order']

    def __str__(self):
        return f"Phase {self.phase}: {self.skill_gap.skill.name}"
