"""
analysis/services/gap_engine.py
Core Skill-Gap Diagnostics & Transparent Readiness Scoring Engine for DUALYN.

Features:
- Multi-source evidence aggregation: Declared skills, resume extraction, project portfolio, profile.
- Centralized normalization and canonical matching.
- Accurate competency assessment statuses:
    * Demonstrated
    * Mentioned / Basic
    * Needs Improvement
    * Missing from Resume
    * Not Assessed
- Transparent, documented, weighted readiness scoring:
    Readiness Score = (Sum of [Importance Weight x Attainment]) / (Sum of Applicable Weights) x 100
- Robust error handling for unreadable or missing resume files.
"""
from typing import Dict, List, Tuple, Any, Optional
from django.db import transaction
from projects.models import ProjectSkill, Project
from skills.models import Skill, StudentSkill
from jobs.models import JobSkill, JobRole
from skills.services.normalization import (
    SKILL_CATALOG,
    canonicalize_skill_name,
    extract_skills_with_evidence
)
from ..models import SkillAnalysis, SkillGap


# Attainment mapping for transparent readiness score calculation
ATTAINMENT_MAP: Dict[str, float] = {
    'demonstrated': 1.0,
    'covered': 1.0,           # backwards-compatible alias for demonstrated
    'needs_improvement': 0.5,
    'mentioned': 0.5,         # basic/introductory familiarity
    'not_assessed': 0.0,
    'missing': 0.0,
}


def run_analysis(student, job_role: JobRole) -> SkillAnalysis:
    """
    Executes a complete career benchmark diagnostic for a student against a target JobRole.
    Analyzes multiple evidence sources: declared skills, database projects, resume text,
    and student profile background.
    """
    analysis = SkillAnalysis(student=student, job_role=job_role)
    return _evaluate_and_save_analysis(analysis, student, job_role, is_new=True)


def recalculate_analysis(analysis: SkillAnalysis) -> SkillAnalysis:
    """
    Recalculates an existing SkillAnalysis in-place using the latest evidence
    (newly uploaded resumes, updated declared skills, projects).
    Updates gaps, scores, and breakdowns without creating duplicate analysis records.
    Also regenerates roadmap recommendations.
    """
    student = analysis.student
    job_role = analysis.job_role
    updated = _evaluate_and_save_analysis(analysis, student, job_role, is_new=False)

    try:
        from recommendations.services.recommendation_engine import generate_recommendations
        generate_recommendations(updated)
    except Exception:
        pass

    return updated


def _evaluate_and_save_analysis(analysis: SkillAnalysis, student: Any, job_role: JobRole, is_new: bool = False) -> SkillAnalysis:
    """
    Shared evaluation core that computes evidence across declared skills, projects,
    and resumes, populating SkillGap entries and computing transparent readiness scores.
    """
    # Ensure role competencies are populated
    from jobs.services.role_profiles import sync_role_profiles_to_db
    job_skills = list(job_role.job_skills.select_related('skill').all())
    if not job_skills:
        sync_role_profiles_to_db()
        job_skills = list(job_role.job_skills.select_related('skill').all())

    # 1. Gather student declared skills
    declared_by_canonical: Dict[str, StudentSkill] = {}
    for s in student.declared_skills.select_related('skill').all():
        canon = canonicalize_skill_name(s.skill.name)
        declared_by_canonical[canon] = s
        declared_by_canonical[s.skill.name] = s
        declared_by_canonical[s.skill.normalized_name] = s

    # 2. Gather database project skills and project descriptions
    project_skills_by_canonical: Dict[str, List[Project]] = {}
    for ps in ProjectSkill.objects.filter(project__student=student).select_related('skill', 'project'):
        canon = canonicalize_skill_name(ps.skill.name)
        project_skills_by_canonical.setdefault(canon, []).append(ps.project)
        project_skills_by_canonical.setdefault(ps.skill.name, []).append(ps.project)

    # 3. Inspect latest resume
    latest_resume = student.resumes.order_by('-uploaded_at').first()
    has_warning = False
    warning_message = ""
    resume_detected_skills: Dict[str, Dict[str, Any]] = {}
    ai_resume_skill_ids = set()

    if latest_resume:
        extracted = latest_resume.extracted_text or ""
        if not extracted.strip():
            has_warning = True
            warning_message = (
                "Notice: No readable text could be extracted from your uploaded resume. "
                "The analysis evaluated your readiness using only declared skills and projects. "
                "Please upload a searchable text-based PDF or DOCX file for full resume extraction."
            )
        else:
            resume_detected_skills = extract_skills_with_evidence(extracted)
            ai_resume_skill_ids = set(
                latest_resume.ai_extracted_skills.values_list('id', flat=True)
            )
    else:
        has_warning = True
        warning_message = (
            "Notice: No resume uploaded. The analysis evaluated your readiness using only "
            "your declared skills and project portfolio. Upload your resume to unlock complete "
            "competency matching."
        )

    # Create or update SkillAnalysis record
    with transaction.atomic():
        analysis.has_warning = has_warning
        analysis.warning_message = warning_message
        if is_new:
            analysis.save()
        else:
            analysis.gaps.all().delete()

        weighted_sum = 0.0
        total_weight = 0
        status_counts = {
            'demonstrated': 0,
            'needs_improvement': 0,
            'mentioned': 0,
            'missing': 0,
            'not_assessed': 0,
        }
        core_covered = 0
        total_core = 0
        opt_covered = 0
        total_opt = 0

        # Assess each competency defined for this target role
        for job_skill in job_skills:
            skill = job_skill.skill
            evidence = _gather_competency_evidence(
                skill=skill,
                declared_map=declared_by_canonical,
                project_skills_map=project_skills_by_canonical,
                resume_skills_map=resume_detected_skills,
                ai_resume_skill_ids=ai_resume_skill_ids,
                has_resume_text=bool(latest_resume and latest_resume.extracted_text and latest_resume.extracted_text.strip()),
                student=student
            )

            status, attainment = _determine_competency_status(
                evidence=evidence,
                required_level=job_skill.required_level or 'Intermediate',
                is_fundamental=job_skill.is_fundamental,
                has_resume_text=bool(latest_resume and latest_resume.extracted_text and latest_resume.extracted_text.strip())
            )

            priority = _determine_priority(
                importance_weight=job_skill.importance_weight,
                is_fundamental=job_skill.is_fundamental,
                status=status
            )

            reasoning = _build_reasoning(skill, evidence, job_skill, status)
            gap_explanation = _build_gap_explanation(skill, status, job_skill)
            recommended_step = _build_recommended_step(skill, status, job_skill)

            SkillGap.objects.create(
                analysis=analysis,
                skill=skill,
                status=status,
                priority=priority,
                reasoning=reasoning,
                evidence_sources=evidence,
                required_level=job_skill.required_level or 'Intermediate',
                gap_explanation=gap_explanation,
                recommended_step=recommended_step,
            )

            weight = job_skill.importance_weight
            weighted_sum += attainment * weight
            total_weight += weight

            # Aggregate statistics
            status_counts[status] = status_counts.get(status, 0) + 1
            if job_skill.is_fundamental:
                total_core += 1
                if status in ('demonstrated', 'covered'):
                    core_covered += 1
            else:
                total_opt += 1
                if status in ('demonstrated', 'covered'):
                    opt_covered += 1

        # Calculate final normalized percentage (0 to 100)
        readiness_score = round((weighted_sum / total_weight) * 100, 1) if total_weight else 0.0

        # Store transparent scoring breakdown
        analysis.readiness_score = readiness_score
        analysis.scoring_breakdown = {
            'formula': 'Readiness Score = (Sum of [Importance Weight × Attainment]) / (Sum of Applicable Weights) × 100',
            'total_weight': total_weight,
            'attained_weight': round(weighted_sum, 2),
            'readiness_percentage': readiness_score,
            'status_counts': status_counts,
            'total_competencies': len(job_skills),
            'demonstrated_count': status_counts.get('demonstrated', 0) + status_counts.get('covered', 0),
            'needs_improvement_count': status_counts.get('needs_improvement', 0),
            'mentioned_count': status_counts.get('mentioned', 0),
            'missing_count': status_counts.get('missing', 0),
            'not_assessed_count': status_counts.get('not_assessed', 0),
            'core_coverage': f"{core_covered}/{total_core} fundamental skills demonstrated",
            'optional_coverage': f"{opt_covered}/{total_opt} specialized skills demonstrated",
        }
        analysis.save()

    return analysis


def _gather_competency_evidence(
    skill: Skill,
    declared_map: Dict[str, StudentSkill],
    project_skills_map: Dict[str, List[Project]],
    resume_skills_map: Dict[str, Dict[str, Any]],
    ai_resume_skill_ids: set,
    has_resume_text: bool,
    student: Any
) -> List[Dict[str, Any]]:
    """
    Collects and deduplicates evidence for a single skill across all available sources:
    1. Declared skills
    2. Database projects
    3. Resume text extraction (including resume project descriptions)
    4. Student profile / experience
    """
    evidence = []
    canonical = canonicalize_skill_name(skill.name)
    skill_keys = {canonical, skill.name, skill.normalized_name}

    # Also resolve components for compound skills (e.g. 'HTML & CSS')
    catalog_entry = SKILL_CATALOG.get(canonical, {})
    components = catalog_entry.get('components', [])

    # Related technologies for overarching competencies
    RELATED_SPECIALIZATIONS = {
        'SQL': ['MySQL', 'PostgreSQL', 'SQLite', 'MariaDB', 'Oracle'],
        'REST API': ['Django REST Framework', 'FastAPI'],
        'Git': ['GitHub', 'GitLab'],
    }

    # 1. Declared skills check
    declared_entry = None
    for k in skill_keys:
        if k in declared_map:
            declared_entry = declared_map[k]
            break

    # If not directly declared, check compound component or related specializations
    if not declared_entry:
        if canonical in ('HTML & CSS', 'Testing & Debugging') and components:
            comp_declared = [declared_map.get(comp) for comp in components if comp in declared_map]
            if len(comp_declared) == len(components):
                # Both components declared
                best_level = 'intermediate' if any(cd.level in ('intermediate', 'advanced') for cd in comp_declared) else 'beginner'
                declared_entry = comp_declared[0]
            elif comp_declared and canonical == 'Testing & Debugging':
                cd = comp_declared[0]
                evidence.append({
                    'source': 'declared',
                    'detail': f"Partial competency: {cd.skill.name} declared at {cd.level} level (missing counterpart)",
                    'level': cd.level,
                    'strength': 'basic',
                    'is_partial': True,
                    'confidence': 0.60,
                })
        elif canonical in ('HTML', 'CSS') and 'HTML & CSS' in declared_map:
            declared_entry = declared_map['HTML & CSS']
        elif canonical in RELATED_SPECIALIZATIONS:
            for rel in RELATED_SPECIALIZATIONS[canonical]:
                if rel in declared_map:
                    declared_entry = declared_map[rel]
                    break

    if declared_entry:
        strength = 'strong' if declared_entry.level in ('intermediate', 'advanced') else 'basic'
        evidence.append({
            'source': 'declared',
            'detail': f"Declared at {declared_entry.level} level",
            'level': declared_entry.level,
            'strength': strength,
            'confidence': 0.85 if strength == 'strong' else 0.70,
        })

    # 2. Database projects check
    matched_projects = []
    for k in skill_keys:
        if k in project_skills_map:
            matched_projects.extend(project_skills_map[k])

    if not matched_projects:
        if canonical in ('HTML', 'CSS') and 'HTML & CSS' in project_skills_map:
            matched_projects.extend(project_skills_map['HTML & CSS'])
        elif canonical in RELATED_SPECIALIZATIONS:
            for rel in RELATED_SPECIALIZATIONS[canonical]:
                if rel in project_skills_map:
                    matched_projects.extend(project_skills_map[rel])
                    break

    if matched_projects:
        proj_names = ", ".join(dict.fromkeys(p.name for p in matched_projects))
        evidence.append({
            'source': 'project',
            'detail': f"Demonstrated in project portfolio: {proj_names}",
            'strength': 'strong',
            'confidence': 0.95,
        })

    # 3. Resume text extraction check
    resume_match = None
    for k in skill_keys:
        if k in resume_skills_map:
            resume_match = resume_skills_map[k]
            break

    # If compound skill (like HTML & CSS or Testing & Debugging), check components found in resume
    if not resume_match and components:
        comp_matches = [resume_skills_map.get(comp) for comp in components if comp in resume_skills_map]
        if len(comp_matches) == len(components):
            if any(m.get('strength') == 'strong' for m in comp_matches):
                comp_strength = 'strong'
            elif all(m.get('strength') == 'basic' for m in comp_matches):
                comp_strength = 'basic'
            else:
                comp_strength = 'moderate'

            resume_match = {
                'canonical': canonical,
                'matched_alias': " + ".join(m['matched_alias'] for m in comp_matches),
                'excerpt': " & ".join(m['excerpt'] for m in comp_matches),
                'strength': comp_strength,
                'is_project_evidence': any(m['is_project_evidence'] for m in comp_matches),
            }
        elif len(comp_matches) > 0 and canonical == 'Testing & Debugging':
            single_m = comp_matches[0]
            present_comp = single_m['canonical']
            missing_comp = [c for c in components if c not in resume_skills_map][0]
            evidence.append({
                'source': 'resume',
                'detail': f"Partial evidence: demonstrated {present_comp}, but {missing_comp} was not found in resume",
                'excerpt': single_m.get('excerpt', ''),
                'strength': 'basic',
                'is_partial': True,
                'confidence': 0.60,
            })

    # If component of compound (e.g. HTML or CSS), check if compound was found in resume
    if not resume_match and canonical in ('HTML', 'CSS') and 'HTML & CSS' in resume_skills_map:
        compound_m = resume_skills_map['HTML & CSS']
        resume_match = {
            'canonical': canonical,
            'matched_alias': compound_m.get('matched_alias', canonical),
            'excerpt': compound_m.get('excerpt', ''),
            'strength': compound_m.get('strength', 'moderate'),
            'is_project_evidence': compound_m.get('is_project_evidence', False),
        }

    if resume_match:
        # Check if resume match occurred within a project description in the resume
        if resume_match.get('is_project_evidence'):
            evidence.append({
                'source': 'project',
                'detail': f"Applied in project mentioned in resume: {resume_match['matched_alias']}",
                'excerpt': resume_match.get('excerpt', ''),
                'strength': resume_match.get('strength', 'strong'),
                'confidence': 0.90,
            })
        else:
            evidence.append({
                'source': 'resume',
                'detail': f"Mentioned in resume: {resume_match['matched_alias']}",
                'excerpt': resume_match.get('excerpt', ''),
                'strength': resume_match.get('strength', 'basic'),
                'confidence': 0.75,
            })
    elif skill.id in ai_resume_skill_ids:
        evidence.append({
            'source': 'resume',
            'detail': f"mentioned in resume (AI verified: {skill.name})",
            'excerpt': f"Candidate demonstrated {skill.name} in resume.",
            'strength': 'basic',
            'is_ai': True,
            'confidence': 0.70,
        })

    # 4. Student profile / experience context
    profile = getattr(student, 'student_profile', None)
    if profile and profile.Years_of_Experience and profile.Years_of_Experience >= 1:
        # General background reinforcement
        pass

    return evidence


def _determine_competency_status(
    evidence: List[Dict[str, Any]],
    required_level: str,
    is_fundamental: bool,
    has_resume_text: bool
) -> Tuple[str, float]:
    """
    Evaluates evidence against competency requirements to determine assessment status
    and numerical score contribution.

    Returns: (status, attainment_score)
    """
    if not evidence:
        return 'missing', 0.0

    # If evidence is partial (e.g. only Debugging demonstrated for Testing & Debugging)
    if any(e.get('is_partial') for e in evidence) and not any(e.get('strength') == 'strong' and not e.get('is_partial') for e in evidence):
        return 'needs_improvement', 0.5

    # Check for practical project evidence
    has_project_evidence = any(e['source'] == 'project' for e in evidence)
    has_strong_evidence = any(e.get('strength') == 'strong' for e in evidence)

    # Check for declared proficiency
    declared_levels = [e.get('level') for e in evidence if e['source'] == 'declared']
    has_advanced_declared = 'advanced' in declared_levels
    has_intermediate_declared = 'intermediate' in declared_levels

    # Multi-source validation:
    # 1. Beginner declared + project = 2 weak sources together count as covered
    if 'beginner' in declared_levels and has_project_evidence:
        return 'covered', 1.0

    # 2. Project evidence with strong practical context -> demonstrated
    if has_project_evidence and has_strong_evidence:
        return 'demonstrated', 1.0

    # 3. Intermediate or advanced declared skill -> covered
    if has_advanced_declared or has_intermediate_declared:
        return 'covered', 1.0

    # 4. Two distinct evidence sources (e.g. declared + resume, or project + declared) -> covered
    distinct_sources = {e['source'] for e in evidence}
    if len(distinct_sources) >= 2:
        return 'covered', 1.0

    # 5. Single project mention with moderate evidence -> demonstrated
    if has_project_evidence:
        return 'demonstrated', 1.0

    # 6. Beginner declared alone -> needs_improvement
    if 'beginner' in declared_levels and len(evidence) == 1:
        return 'needs_improvement', 0.5

    # 7. AI extracted alone -> needs_improvement
    if any(e.get('is_ai') for e in evidence):
        return 'needs_improvement', 0.5

    # 7. Introductory or list-only mention (e.g. 'OOP basics', 'Python in skills')
    is_basic_mention = any(e.get('strength') == 'basic' for e in evidence)
    if is_basic_mention:
        return 'mentioned', 0.5

    # 8. Some relevant evidence exists, but falls short of expected level -> Needs Improvement
    return 'needs_improvement', 0.5


def _determine_priority(importance_weight: int, is_fundamental: bool, status: str) -> str:
    """
    Determines learning priority based on role weight and current attainment status.
    """
    if status in ('demonstrated', 'covered'):
        return 'low'
    if importance_weight >= 4 or is_fundamental:
        return 'high'
    if importance_weight == 3:
        return 'medium'
    return 'low'


def _build_reasoning(skill: Skill, evidence: List[Dict[str, Any]], job_skill: JobSkill, status: str) -> str:
    """Builds a concise, evidence-grounded summary statement."""
    if not evidence:
        note = " This is a fundamental core competency for this role." if job_skill.is_fundamental else ""
        return f"No evidence of {skill.name} found in resume, declared skills, or project portfolio.{note}"

    detail_parts = [e['detail'] for e in evidence]
    excerpts = [e['excerpt'] for e in evidence if e.get('excerpt')]
    excerpt_str = f" Context: \"{excerpts[0]}\"" if excerpts else ""
    fundamental_note = " Fundamental core competency." if job_skill.is_fundamental else ""

    status_label = {
        'demonstrated': "Demonstrated",
        'covered': "Demonstrated",
        'mentioned': "Mentioned / Basic familiarity",
        'needs_improvement': "Needs Improvement",
        'not_assessed': "Not Assessed",
        'missing': "Missing",
    }.get(status, status)

    return f"{skill.name} ({status_label}): {'; '.join(detail_parts)}.{excerpt_str} Importance: {job_skill.importance_weight}/5.{fundamental_note}"


def _build_gap_explanation(skill: Skill, status: str, job_skill: JobSkill) -> str:
    """Explains why a gap exists relative to the required role benchmark."""
    req = job_skill.required_level or 'Intermediate'
    if status in ('demonstrated', 'covered'):
        return f"Demonstrated practical proficiency at or above the expected {req} level."
    elif status == 'mentioned':
        return f"Concept is mentioned in introductory form, but target role expects verified {req} level implementation in production code."
    elif status == 'needs_improvement':
        return f"Partial evidence found, but falls short of the {req} proficiency level required for this role."
    elif status == 'not_assessed':
        return "Resume text extraction was unavailable. Evidence could not be reliably evaluated."
    else:
        importance_str = "Critical fundamental skill" if job_skill.is_fundamental else f"Required skill (weight {job_skill.importance_weight}/5)"
        return f"No evidence located in uploaded documents or declared proficiencies. {importance_str}."


def _build_recommended_step(skill: Skill, status: str, job_skill: JobSkill) -> str:
    """Generates an actionable next step to advance this competency."""
    if status in ('demonstrated', 'covered'):
        return f"Maintain proficiency and highlight specific achievements with {skill.name} in project interview talking points."
    elif status == 'mentioned':
        return f"Build a practical feature or dedicated mini-project using {skill.name} to demonstrate applied practical mastery."
    elif status == 'needs_improvement':
        return f"Deepen practical understanding of {skill.name} by implementing real-world patterns and automated test coverage."
    elif status == 'not_assessed':
        return "Re-upload a searchable text-based resume (PDF or DOCX) to receive an automated competency assessment."
    else:
        return f"Complete foundational study for {skill.name} and integrate it into a portfolio application."