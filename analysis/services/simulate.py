"""
analysis/services/simulate.py
"What if I learn this?" Simulator Service for DUALYN.

Computes projected match readiness scores for a saved SkillAnalysis snapshot
as if specified gap competencies were fully mastered, without persisting
or altering database records.
"""
from typing import Any, Iterable, Union, Set
from jobs.models import JobSkill
from .gap_engine import ATTAINMENT_MAP, compute_readiness_score


def simulate_score(analysis: Any, skill_ids: Union[Iterable[Any], Any]) -> float:
    """
    Recomputes the weighted readiness score of a saved SkillAnalysis instance
    as if the specified gap skills were fully attained (attainment = 1.0).

    Reuses the gap engine's ATTAINMENT_MAP and weighted scoring formula.
    Pure function: performs zero database writes or mutations.
    """
    if isinstance(skill_ids, (int, str)):
        skill_ids = [skill_ids]

    parsed_ids: Set[int] = set()
    if skill_ids:
        for sid in skill_ids:
            try:
                parsed_ids.add(int(sid))
            except (ValueError, TypeError):
                continue

    gaps = list(analysis.gaps.select_related('skill').all())
    if not gaps:
        return float(analysis.readiness_score)

    analysis_gap_skill_ids = {g.skill_id for g in gaps}
    active_simulated_ids = parsed_ids & analysis_gap_skill_ids

    # If no valid gap skills are selected, score is unchanged
    if not active_simulated_ids:
        return float(analysis.readiness_score)

    job_skills_map = dict(
        JobSkill.objects.filter(job_role=analysis.job_role).values_list('skill_id', 'importance_weight')
    )

    weighted_sum = 0.0
    total_weight = 0

    for gap in gaps:
        weight = job_skills_map.get(gap.skill_id, 3)
        if gap.skill_id in active_simulated_ids:
            attainment = 1.0
        else:
            attainment = ATTAINMENT_MAP.get(gap.status, 0.0)

        weighted_sum += attainment * weight
        total_weight += weight

    projected = compute_readiness_score(weighted_sum, total_weight)
    return max(float(analysis.readiness_score), projected)

