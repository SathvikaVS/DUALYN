from collections import defaultdict
from typing import List, Dict, Any
from jobs.models import JobRole, JobSkill
from jobs.services.role_profiles import sync_role_profiles_to_db
from .gap_engine import gather_student_evidence, evaluate_role_readiness


class GapItem(dict):
    """Dictionary subclass that allows attribute-style access for templates and tests."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class RoleFit(dict):
    """Dictionary subclass that allows attribute-style access for templates and tests."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


def rank_roles_for(student: Any) -> List[Dict[str, Any]]:
    """
    Ranks every JobRole by how ready the student is, without saving anything to the database.
    Returns a list of dicts:
        {
            'role': <JobRole>,
            'score': <float>,
            'covered_count': <int>,
            'missing_count': <int>,
            'top_gaps': [<GapItem>, <GapItem>, <GapItem>],
        }
    sorted by score descending. Roles with no JobSkill rows are skipped.
    Job skills are loaded in a single query to prevent N+1 queries.
    """
    # 1. Gather student evidence once (reused across all role evaluations)
    student_evidence = gather_student_evidence(student)

    # 2. Load all job roles and job skills in single queries (no N+1)
    roles = list(JobRole.objects.all())
    all_job_skills = list(JobSkill.objects.select_related('skill').all())
    if not all_job_skills and not roles:
        sync_role_profiles_to_db()
        roles = list(JobRole.objects.all())
        all_job_skills = list(JobSkill.objects.select_related('skill').all())

    job_skills_by_role = defaultdict(list)
    for js in all_job_skills:
        job_skills_by_role[js.job_role_id].append(js)

    priority_map = {'high': 0, 'medium': 1, 'low': 2}
    ranked: List[Dict[str, Any]] = []

    for role in roles:
        skills = job_skills_by_role.get(role.id, [])
        if not skills:
            # Skip roles with no JobSkill rows
            continue

        result = evaluate_role_readiness(
            student=student,
            job_role=role,
            student_evidence=student_evidence,
            job_skills=skills,
        )

        # Identify gaps: competencies not in ('demonstrated', 'covered')
        gaps = [g for g in result['gaps_data'] if g['status'] not in ('demonstrated', 'covered')]

        # Sort gaps by priority: high -> medium -> low, fundamental first, highest weight first
        sorted_gaps = sorted(
            gaps,
            key=lambda g: (
                priority_map.get(g['priority'], 3),
                0 if g.get('is_fundamental') else 1,
                -g.get('importance_weight', 0),
                g['skill'].name,
            )
        )
        top_3_gaps = [GapItem(g) for g in sorted_gaps[:3]]

        ranked.append(RoleFit({
            'role': role,
            'score': result['readiness_score'],
            'covered_count': result['covered_count'],
            'missing_count': result['missing_count'],
            'top_gaps': top_3_gaps,
        }))

    # Sort descending by score, tie-break by role title for deterministic order
    ranked.sort(key=lambda r: (-r['score'], r['role'].title))
    return ranked

