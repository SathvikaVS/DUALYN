from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from skills.models import Skill, StudentSkill
from jobs.models import JobRole, JobSkill
from projects.models import Project
from resumes.models import Resume
from analysis.models import SkillAnalysis
from analysis.services.gap_engine import run_analysis
from analysis.services.freshness import evidence_changed_since
from recommendations.services.recommendation_engine import generate_recommendations


class SnapshotImmutabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='password123')
        self.other_user = User.objects.create_user('bob', password='password123')

        self.python, _ = Skill.objects.get_or_create(name='Python')
        self.django, _ = Skill.objects.get_or_create(name='Django')
        self.docker, _ = Skill.objects.get_or_create(name='Docker')

        self.job, _ = JobRole.objects.get_or_create(title='Backend Developer')
        JobSkill.objects.create(job_role=self.job, skill=self.python, importance_weight=5, is_fundamental=True)
        JobSkill.objects.create(job_role=self.job, skill=self.django, importance_weight=4)
        JobSkill.objects.create(job_role=self.job, skill=self.docker, importance_weight=3)

        # Alice starts with only Python
        StudentSkill.objects.create(student=self.user, skill=self.python, level='intermediate')

        self.analysis = run_analysis(self.user, self.job)
        generate_recommendations(self.analysis)
        self.initial_score = self.analysis.readiness_score
        self.initial_gap_statuses = {g.skill.name: g.status for g in self.analysis.gaps.all()}

        self.client = Client()
        self.client.force_login(self.user)

    def _assert_analysis_unchanged(self):
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.readiness_score, self.initial_score)
        current_gap_statuses = {g.skill.name: g.status for g in self.analysis.gaps.all()}
        self.assertEqual(current_gap_statuses, self.initial_gap_statuses)

    def test_opening_report_does_not_change_analysis(self):
        # Even if a resume was uploaded after the analysis was created
        Resume.objects.create(
            student=self.user,
            extracted_text="I know Python and Django and Docker."
        )
        url = reverse('analysis:report', kwargs={'pk': self.analysis.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self._assert_analysis_unchanged()

    def test_opening_dashboard_does_not_change_analysis(self):
        Resume.objects.create(
            student=self.user,
            extracted_text="I know Python and Django and Docker."
        )
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self._assert_analysis_unchanged()

    def test_adding_skill_does_not_change_existing_analysis(self):
        url = reverse('skills:my_skills')
        response = self.client.post(url, {
            'skill': self.django.pk,
            'level': 'advanced',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudentSkill.objects.filter(student=self.user, skill=self.django).exists())
        self._assert_analysis_unchanged()

    def test_removing_skill_does_not_change_existing_analysis(self):
        entry = StudentSkill.objects.get(student=self.user, skill=self.python)
        url = reverse('skills:remove_skill', kwargs={'pk': entry.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StudentSkill.objects.filter(student=self.user, skill=self.python).exists())
        self._assert_analysis_unchanged()

    def test_syncing_resume_does_not_change_existing_analysis(self):
        resume_file = SimpleUploadedFile('test.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        resume = Resume.objects.create(student=self.user, file=resume_file, extracted_text="Python Django")
        resume.ai_extracted_skills.set([self.django])

        url = reverse('resumes:sync', kwargs={'pk': resume.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self._assert_analysis_unchanged()

    def test_refresh_creates_new_analysis_and_keeps_old_one(self):
        # Add Django so the new analysis has higher score
        StudentSkill.objects.create(student=self.user, skill=self.django, level='advanced')

        initial_count = SkillAnalysis.objects.filter(student=self.user, job_role=self.job).count()
        url = reverse('analysis:refresh', kwargs={'pk': self.analysis.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self._assert_analysis_unchanged()

        # Check a new analysis exists
        analyses = SkillAnalysis.objects.filter(student=self.user, job_role=self.job).order_by('-created_at')
        self.assertEqual(analyses.count(), initial_count + 1)
        new_analysis = analyses.first()
        self.assertNotEqual(new_analysis.pk, self.analysis.pk)
        self.assertRedirects(response, reverse('analysis:report', kwargs={'pk': new_analysis.pk}))
        self.assertGreater(new_analysis.readiness_score, self.analysis.readiness_score)

    def test_refresh_is_post_only(self):
        url = reverse('analysis:refresh', kwargs={'pk': self.analysis.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_refresh_rejects_other_users(self):
        other_client = Client()
        other_client.force_login(self.other_user)
        url = reverse('analysis:refresh', kwargs={'pk': self.analysis.pk})
        response = other_client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_refresh_rejects_anonymous_users(self):
        anon_client = Client()
        url = reverse('analysis:refresh', kwargs={'pk': self.analysis.pk})
        response = anon_client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class FreshnessAndBannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('charlie', password='password123')
        self.job, _ = JobRole.objects.get_or_create(title='DevOps Engineer')
        self.analysis = run_analysis(self.user, self.job)

        # Move analysis.created_at into the past so subsequent creations are strictly newer
        past_time = timezone.now() - timedelta(hours=2)
        SkillAnalysis.objects.filter(pk=self.analysis.pk).update(created_at=past_time)
        self.analysis.refresh_from_db()

        self.client = Client()
        self.client.force_login(self.user)

    def test_evidence_changed_since_initially_false(self):
        self.assertFalse(evidence_changed_since(self.analysis))

    def test_evidence_changed_since_true_with_newer_resume(self):
        resume_file = SimpleUploadedFile('sample.pdf', b'%PDF-1.4 sample', content_type='application/pdf')
        Resume.objects.create(student=self.user, file=resume_file)
        self.assertTrue(evidence_changed_since(self.analysis))

    def test_evidence_changed_since_true_with_newer_skill(self):
        skill, _ = Skill.objects.get_or_create(name='Terraform')
        StudentSkill.objects.create(student=self.user, skill=skill, level='intermediate')
        self.assertTrue(evidence_changed_since(self.analysis))

    def test_evidence_changed_since_true_with_newer_project(self):
        Project.objects.create(student=self.user, name='CI/CD Pipeline')
        self.assertTrue(evidence_changed_since(self.analysis))

    def test_stale_banner_appears_in_report_and_dashboard_when_stale(self):
        skill, _ = Skill.objects.get_or_create(name='Kubernetes')
        StudentSkill.objects.create(student=self.user, skill=skill, level='intermediate')

        # Report view
        report_url = reverse('analysis:report', kwargs={'pk': self.analysis.pk})
        response = self.client.get(report_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_stale'])
        self.assertContains(response, "You've added new information since this check")
        self.assertContains(response, reverse('analysis:refresh', kwargs={'pk': self.analysis.pk}))
        self.assertContains(response, "Check again with latest info")

        # Dashboard view
        dash_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_response.status_code, 200)
        self.assertTrue(dash_response.context['latest_is_stale'])
        self.assertContains(dash_response, "You've added new information since this check")
        self.assertContains(dash_response, reverse('analysis:refresh', kwargs={'pk': self.analysis.pk}))
        self.assertContains(dash_response, "Check again with latest info")
