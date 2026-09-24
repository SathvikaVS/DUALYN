from ..models import Recommendation, LearningRoadmap, RoadmapItem
from .content_library import get_steps_for_skill


def generate_recommendations(analysis):
    """
    Creates Recommendation + LearningRoadmap + RoadmapItem records
    for every non-covered SkillGap in a completed SkillAnalysis.
    """
    gaps_needing_action = analysis.gaps.exclude(status='covered').select_related('skill')

    for gap in gaps_needing_action:
        Recommendation.objects.create(
            analysis=analysis,
            skill_gap=gap,
            steps=get_steps_for_skill(gap.skill.name),
        )

    roadmap = LearningRoadmap.objects.create(analysis=analysis)
    _build_roadmap(roadmap, gaps_needing_action)
    return roadmap


def _build_roadmap(roadmap, gaps):
    """
    Sorts gaps into phases:
    Phase 1: fundamental/high-priority missing skills
    Phase 2: other missing skills
    Phase 3: needs_improvement skills
    Phase 4: reserved for a portfolio project suggestion (Phase 12/17 territory)
    """
    order = 0
    for gap in gaps:
        if gap.status == 'missing' and gap.priority == 'high':
            phase = 1
        elif gap.status == 'missing':
            phase = 2
        else:
            phase = 3

        RoadmapItem.objects.create(roadmap=roadmap, skill_gap=gap, phase=phase, order=order)
        order += 1