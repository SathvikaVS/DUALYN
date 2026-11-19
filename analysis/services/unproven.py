"""
analysis/services/unproven.py
Identifies required job competencies that a student claims (via declared skills
or resume extraction) but has not yet proven with a portfolio project.
"""
from typing import List, Dict, Any
from skills.models import Skill
from skills.services.normalization import canonicalize_skill_name
from projects.models import ProjectSkill

DEFAULT_PROJECT_IDEA = "Build a portfolio project to demonstrate practical proficiency in this skill."


class UnprovenClaim(dict):
    """
    Dictionary subclass supporting both dict key access (e.g. claim['skill'])
    and attribute access (e.g. claim.skill) for convenience in templates and services.
    """
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'UnprovenClaim' object has no attribute '{name}'")


def unproven_claims(analysis: Any) -> List[Dict[str, Any]]:
    """
    Returns required competencies for the analysis job role that are claimed via
    a declared StudentSkill or resume extraction, but have no ProjectSkill on any
    of the student's projects.

    Each item:
    {
        'skill': Skill instance,
        'claimed_via': str ("Declared skill", "Resume", or "Declared skill & Resume"),
        'project_idea': str (from matching RoadmapItem.task_idea or fallback text)
    }

    Pure function: strictly read-only, performs zero DB writes, scores unchanged.
    """
    student = analysis.student

    # 1. Gather all project skill IDs and canonical names for this student
    student_project_skill_ids = set(
        ProjectSkill.objects.filter(project__student=student).values_list('skill_id', flat=True)
    )
    student_project_canonicals = set()
    for ps in ProjectSkill.objects.filter(project__student=student).select_related('skill'):
        student_project_canonicals.add(canonicalize_skill_name(ps.skill.name))
        student_project_canonicals.add(ps.skill.name.lower())

    # 2. Gather declared skill IDs for this student
    declared_skill_ids = set(
        student.declared_skills.values_list('skill_id', flat=True)
    )

    # 3. Gather resume skills for this student
    resume_skill_ids = set()
    latest_resume = student.resumes.order_by('-uploaded_at').first()
    if latest_resume:
        resume_skill_ids = set(
            latest_resume.ai_extracted_skills.values_list('id', flat=True)
        )

    # 4. Map roadmap task ideas if roadmap exists
    roadmap_ideas_by_gap_id: Dict[int, str] = {}
    roadmap_ideas_by_skill_id: Dict[int, str] = {}
    roadmap = getattr(analysis, 'roadmap', None)
    if roadmap:
        for item in roadmap.items.select_related('skill_gap').all():
            if item.task_idea and item.task_idea.strip():
                roadmap_ideas_by_gap_id[item.skill_gap_id] = item.task_idea.strip()
                if item.skill_gap and item.skill_gap.skill_id:
                    roadmap_ideas_by_skill_id[item.skill_gap.skill_id] = item.task_idea.strip()

    unproven_list: List[Dict[str, Any]] = []

    # 5. Evaluate each required competency in the analysis
    gaps = analysis.gaps.select_related('skill').all()
    for gap in gaps:
        skill = gap.skill
        skill_id = skill.id
        canon_name = canonicalize_skill_name(skill.name)

        # Check evidence sources recorded by gap engine
        evidence_sources = gap.evidence_sources or []
        evidence_types = {
            e.get('source') for e in evidence_sources if isinstance(e, dict)
        }

        # Claimed via declared skill?
        is_declared = (
            'declared' in evidence_types
            or skill_id in declared_skill_ids
        )

        # Claimed via resume?
        is_resume = (
            'resume' in evidence_types
            or skill_id in resume_skill_ids
        )

        # If not claimed by either declared or resume, skip (unclaimed gap)
        if not is_declared and not is_resume:
            continue

        # Check if already demonstrated in a project (has ProjectSkill on any student project)
        has_project = (
            skill_id in student_project_skill_ids
            or canon_name in student_project_canonicals
            or skill.name.lower() in student_project_canonicals
        )

        if has_project:
            continue

        # Determine claimed_via label
        if is_declared and is_resume:
            claimed_via = "Declared skill & Resume"
        elif is_declared:
            claimed_via = "Declared skill"
        else:
            claimed_via = "Resume"

        # Determine project idea
        project_idea = (
            roadmap_ideas_by_gap_id.get(gap.id)
            or roadmap_ideas_by_skill_id.get(skill_id)
            or DEFAULT_PROJECT_IDEA
        )

        unproven_list.append(UnprovenClaim({
            'skill': skill,
            'claimed_via': claimed_via,
            'project_idea': project_idea,
        }))

    return unproven_list
