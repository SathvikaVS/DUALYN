from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import os


def validate_resume_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.pdf', '.docx']:
        raise ValidationError('Only PDF and DOCX files are allowed.')


class Resume(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to='resumes/%Y/%m/', validators=[validate_resume_file])
    extracted_text = models.TextField(blank=True)
    headline = models.CharField(max_length=255, blank=True)
    detected_role = models.ForeignKey(
        'jobs.JobRole',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='detected_resumes'
    )
    ai_extracted_skills = models.ManyToManyField('skills.Skill', blank=True, related_name='resumes_mentioning')
    skills_evidence = models.JSONField(default=dict, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.file.name}"

    def get_detected_role(self):
        """
        Returns the detected target JobRole, falling back to dynamic detection
        from extracted_text if not already persisted.
        """
        if self.detected_role:
            return self.detected_role
        if self.extracted_text:
            from jobs.services.role_matcher import detect_target_role_from_resume
            role, _ = detect_target_role_from_resume(self.extracted_text)
            return role
        return None

    def get_headline(self):
        """
        Returns the extracted headline string, falling back to dynamic detection
        from extracted_text if not already persisted.
        """
        if self.headline:
            return self.headline
        if self.extracted_text:
            from jobs.services.role_matcher import extract_headline
            return extract_headline(self.extracted_text) or ""
        return ""

    def get_competencies_with_evidence(self):
        """
        Returns a list of dicts for each competency with its full traceability:
        [
            {
                'skill': Skill,
                'name': 'Python',
                'category': 'Programming',
                'section': 'Projects',
                'sentence': 'Technologies: Python, Django...',
                'matched_alias': 'Python',
                'is_inferred': False,
                'evidence_type': 'explicit',
            },
            ...
        ]
        """
        result = []
        evidence_dict = self.skills_evidence or {}
        for skill in self.ai_extracted_skills.all().order_by('name'):
            ev = evidence_dict.get(skill.name, {})
            result.append({
                'skill': skill,
                'name': skill.name,
                'category': skill.category or 'Technical Skills',
                'section': ev.get('section', 'Parsed Content'),
                'sentence': ev.get('sentence', ''),
                'matched_alias': ev.get('matched_alias', skill.name),
                'is_inferred': ev.get('is_inferred', False),
                'evidence_type': 'inferred' if ev.get('is_inferred') else 'explicit',
            })
        return result

    class Meta:
        ordering = ['-uploaded_at']
