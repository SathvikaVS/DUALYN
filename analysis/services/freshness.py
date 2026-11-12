from resumes.models import Resume
from skills.models import StudentSkill
from projects.models import Project


def evidence_changed_since(analysis) -> bool:
    """
    Returns True if the student has a Resume with uploaded_at > analysis.created_at,
    a StudentSkill with added_at > analysis.created_at, or a Project with created_at > analysis.created_at.
    """
    if not analysis or not getattr(analysis, 'created_at', None):
        return False

    student = analysis.student
    return (
        Resume.objects.filter(student=student, uploaded_at__gt=analysis.created_at).exists()
        or StudentSkill.objects.filter(student=student, added_at__gt=analysis.created_at).exists()
        or Project.objects.filter(student=student, created_at__gt=analysis.created_at).exists()
    )

