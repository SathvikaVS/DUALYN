from projects.models import ProjectSkill
from ..models import SkillAnalysis, SkillGap


def run_analysis(student, job_role):
    """
    Compares a student's evidence (declared skills, resume text, project skills)
    against a job role's required skills. Creates one immutable SkillAnalysis
    with a SkillGap row per required skill.
    """
    job_skills = job_role.job_skills.select_related('skill')

    declared = {s.skill_id: s for s in student.declared_skills.select_related('skill')}
    project_skill_ids = set(
        ProjectSkill.objects.filter(project__student=student).values_list('skill_id', flat=True)
    )
    latest_resume = student.resumes.order_by('-uploaded_at').first()
    resume_text = (latest_resume.extracted_text or '').lower() if latest_resume else ''

    analysis = SkillAnalysis.objects.create(student=student, job_role=job_role)

    weighted_sum = 0
    total_weight = 0

    for job_skill in job_skills:
        skill = job_skill.skill
        evidence = _gather_evidence(skill, declared, project_skill_ids, resume_text)
        status, score = _determine_status(evidence)
        priority = _determine_priority(job_skill.importance_weight, job_skill.is_fundamental, status)
        reasoning = _build_reasoning(skill, evidence, job_skill)

        SkillGap.objects.create(
            analysis=analysis,
            skill=skill,
            status=status,
            priority=priority,
            reasoning=reasoning,
        )

        weighted_sum += score * job_skill.importance_weight
        total_weight += job_skill.importance_weight

    analysis.readiness_score = round((weighted_sum / total_weight) * 100, 1) if total_weight else 0
    analysis.save()
    return analysis


def _gather_evidence(skill, declared, project_skill_ids, resume_text):
    evidence = []
    declared_entry = declared.get(skill.id)
    if declared_entry:
        evidence.append(('declared', declared_entry.level))
    if skill.id in project_skill_ids:
        evidence.append(('project', None))
    if resume_text and skill.normalized_name in resume_text:
        evidence.append(('resume', None))
    return evidence


def _determine_status(evidence):
    if not evidence:
        return 'missing', 0.0

    has_strong_declared = any(
        src == 'declared' and level in ('intermediate', 'advanced') for src, level in evidence
    )
    if has_strong_declared or len(evidence) >= 2:
        return 'covered', 1.0

    return 'needs_improvement', 0.5


def _determine_priority(importance_weight, is_fundamental, status):
    if status == 'covered':
        return 'low'
    if importance_weight >= 4 or is_fundamental:
        return 'high'
    if importance_weight == 3:
        return 'medium'
    return 'low'


def _build_reasoning(skill, evidence, job_skill):
    if not evidence:
        return f"No evidence of {skill.name} found in declared skills, resume, or projects."

    labels = {
        'declared': lambda level: f"declared at {level} level",
        'project': lambda _: "used in a project",
        'resume': lambda _: "mentioned in resume",
    }
    parts = [labels[src](level) for src, level in evidence]
    fundamental_note = " This is a fundamental skill for this role." if job_skill.is_fundamental else ""
    return f"{skill.name}: {', '.join(parts)}. Importance: {job_skill.importance_weight}/5.{fundamental_note}"