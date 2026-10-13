"""
recommendations/services/recommendation_engine.py
Dependency-Aware Learning Roadmap and Actionable Recommendation Engine for DUALYN.

Features:
- Excludes demonstrated/covered competencies (never asks students to re-learn verified skills).
- Organizes skill gaps into a structured pedagogical progression:
    Phase 1: Programming Fundamentals (Python, OOP, DSA, SQL, Git)
    Phase 2: Backend Development (Django, REST API, Testing & Debugging)
    Phase 3: Advanced & Job-Specific Skills (PostgreSQL, Docker, Frontend, NumPy/Pandas)
    Phase 4: Portfolio Capstone Project
- Provides reasons, suggested learning outcomes, and concrete practical tasks for every gap.
"""
from typing import List
from ..models import Recommendation, LearningRoadmap, RoadmapItem
from .content_library import get_skill_metadata, get_steps_for_skill
from skills.services.normalization import canonicalize_skill_name


# Explicit pedagogical priority within each phase
PHASE_PRIORITY_ORDER = {
    # Phase 1
    'Python': 1,
    'Object-Oriented Programming': 2,
    'Data Structures & Algorithms': 3,
    'SQL': 4,
    'Git': 5,
    # Phase 2
    'Django': 10,
    'REST API': 11,
    'Testing & Debugging': 12,
    'Excel': 13,
    'Statistics': 14,
    # Phase 3
    'PostgreSQL': 20,
    'Docker': 21,
    'HTML & CSS': 22,
    'JavaScript': 23,
    'NumPy': 24,
    'Pandas': 25,
    'Power BI': 26,
}


def generate_recommendations(analysis) -> LearningRoadmap:
    """
    Creates Recommendation and LearningRoadmap records for all non-demonstrated SkillGaps.
    Skills that the student has already demonstrated at the required level are excluded.
    """
    # Delete any previous recommendations/roadmap for this analysis if re-running
    Recommendation.objects.filter(analysis=analysis).delete()
    if hasattr(analysis, 'roadmap'):
        analysis.roadmap.delete()

    # Exclude skills that are already demonstrated / covered
    gaps_needing_action = analysis.gaps.exclude(
        status__in=['demonstrated', 'covered']
    ).select_related('skill')

    for gap in gaps_needing_action:
        Recommendation.objects.create(
            analysis=analysis,
            skill_gap=gap,
            steps=get_steps_for_skill(gap.skill.name),
        )

    roadmap = LearningRoadmap.objects.create(analysis=analysis)
    _build_roadmap(roadmap, list(gaps_needing_action))
    return roadmap


def _build_roadmap(roadmap: LearningRoadmap, gaps: List) -> None:
    """
    Sorts skill gaps into a dependency-aware phased sequence:
    Phase 1: Fundamentals (Python, OOP, DSA, SQL, Git)
    Phase 2: Frameworks & APIs (Django, REST APIs, Testing)
    Phase 3: Production, Databases & Specializations (Postgres, Docker, Frontend, Data analysis)
    """
    # Sort gaps by pedagogical dependency, then by priority weight
    def roadmap_sort_key(gap):
        canonical = canonicalize_skill_name(gap.skill.name)
        meta = get_skill_metadata(canonical)
        phase = meta.get('default_phase', 2)
        inner_order = PHASE_PRIORITY_ORDER.get(canonical, 50)
        priority_rank = {'high': 0, 'medium': 1, 'low': 2}.get(gap.priority, 1)
        return (phase, priority_rank, inner_order, gap.skill.name)

    sorted_gaps = sorted(gaps, key=roadmap_sort_key)

    order_counter = 0
    for gap in sorted_gaps:
        canonical = canonicalize_skill_name(gap.skill.name)
        meta = get_skill_metadata(canonical)
        phase = meta.get('default_phase', 2)

        RoadmapItem.objects.create(
            roadmap=roadmap,
            skill_gap=gap,
            phase=phase,
            order=order_counter,
            why_it_matters=meta.get('why_it_matters', ''),
            learning_outcome=meta.get('learning_outcome', ''),
            task_idea=meta.get('task_idea', ''),
        )
        order_counter += 1