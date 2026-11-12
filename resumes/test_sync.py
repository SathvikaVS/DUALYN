from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from skills.models import Skill, StudentSkill
from jobs.models import JobRole, JobSkill
from analysis.models import SkillAnalysis
from analysis.services.gap_engine import run_analysis
from recommendations.services.recommendation_engine import generate_recommendations
from resumes.models import Resume


class ResumeSyncAndUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='password123')
        self.other_user = User.objects.create_user('bob', password='password123')

        self.python, _ = Skill.objects.get_or_create(name='Python')
        self.django_skill, _ = Skill.objects.get_or_create(name='Django')
        self.docker, _ = Skill.objects.get_or_create(name='Docker')

        self.job, _ = JobRole.objects.get_or_create(title='Python Developer')
        JobSkill.objects.get_or_create(job_role=self.job, skill=self.python, defaults={'importance_weight': 5, 'is_fundamental': True})
        JobSkill.objects.get_or_create(job_role=self.job, skill=self.django_skill, defaults={'importance_weight': 4})
        JobSkill.objects.get_or_create(job_role=self.job, skill=self.docker, defaults={'importance_weight': 3})

        # Alice starts with only Python
        StudentSkill.objects.create(student=self.user, skill=self.python, level='intermediate')

        # Existing analysis for Alice
        self.existing_analysis = run_analysis(self.user, self.job)
        generate_recommendations(self.existing_analysis)
        self.initial_score = self.existing_analysis.readiness_score
        self.initial_gaps = {g.skill.name: g.status for g in self.existing_analysis.gaps.all()}

        # A resume belonging to Alice
        resume_file = SimpleUploadedFile('sample.pdf', b'%PDF-1.4 sample', content_type='application/pdf')
        self.resume = Resume.objects.create(
            student=self.user,
            file=resume_file,
            extracted_text="Python Django Developer"
        )
        self.resume.ai_extracted_skills.set([self.python, self.django_skill])

        self.client = Client()
        self.client.force_login(self.user)

    def _assert_existing_analysis_unchanged(self):
        self.existing_analysis.refresh_from_db()
        self.assertEqual(self.existing_analysis.readiness_score, self.initial_score)
        current_gaps = {g.skill.name: g.status for g in self.existing_analysis.gaps.all()}
        self.assertEqual(current_gaps, self.initial_gaps)

    def test_sync_is_post_only(self):
        url = reverse('resumes:sync', kwargs={'pk': self.resume.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_sync_rejects_anonymous_users(self):
        anon_client = Client()
        url = reverse('resumes:sync', kwargs={'pk': self.resume.pk})
        response = anon_client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_sync_rejects_other_users(self):
        other_client = Client()
        other_client.force_login(self.other_user)
        url = reverse('resumes:sync', kwargs={'pk': self.resume.pk})
        response = other_client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_sync_works_for_owner_without_500(self):
        url = reverse('resumes:sync', kwargs={'pk': self.resume.pk})
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        # Check success message
        messages = [m.message for m in response.context['messages']]
        self.assertTrue(any("Run a new check to see how they change your match." in m for m in messages))

    def test_sync_never_changes_existing_analysis(self):
        url = reverse('resumes:sync', kwargs={'pk': self.resume.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self._assert_existing_analysis_unchanged()

    @patch('resumes.views.extract_resume_skills_with_evidence')
    @patch('resumes.views.extract_text_from_resume')
    def test_upload_with_detected_role_adds_new_analysis_and_leaves_old_unchanged(
        self, mock_extract_text, mock_extract_skills
    ):
        mock_extract_text.return_value = "ALICE SMITH\nPython Developer\nProficient in Python, Django, and Docker."
        mock_extract_skills.return_value = (
            [self.python, self.django_skill, self.docker],
            {'Python': {'section': 'Technical Skills', 'sentence': 'Proficient in Python'}}
        )

        initial_count = SkillAnalysis.objects.filter(student=self.user, job_role=self.job).count()
        self.assertEqual(initial_count, 1)

        upload_file = SimpleUploadedFile('new_resume.pdf', b'%PDF-1.4 new', content_type='application/pdf')
        url = reverse('resumes:upload')
        response = self.client.post(url, {'file': upload_file})
        self.assertEqual(response.status_code, 302)

        # Existing analysis is unchanged
        self._assert_existing_analysis_unchanged()

        # A new analysis was added
        analyses = SkillAnalysis.objects.filter(student=self.user, job_role=self.job).order_by('-created_at')
        self.assertEqual(analyses.count(), 2)
        new_analysis = analyses.first()
        self.assertNotEqual(new_analysis.pk, self.existing_analysis.pk)

