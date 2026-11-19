"""
analysis/test_share.py
Tests for the private, expiring, revocable share link feature.
"""
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from skills.models import Skill, StudentSkill
from jobs.models import JobRole, JobSkill
from resumes.models import Resume
from students.models import Student_Profile
from analysis.models import SkillAnalysis, SkillGap, ShareLink
from analysis.services.gap_engine import run_analysis
from recommendations.services.recommendation_engine import generate_recommendations


class ShareLinkTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username='alice_secret_username',
            email='alice_secret_private@example.com',
            password='password123'
        )
        self.bob = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='password123'
        )

        profile, _ = Student_Profile.objects.get_or_create(User=self.alice)
        profile.Full_name = "Alice TestFullname"
        profile.save()

        self.python, _ = Skill.objects.get_or_create(name='Python')
        self.django_skill, _ = Skill.objects.get_or_create(name='Django')

        self.job, _ = JobRole.objects.get_or_create(title='Backend Developer')
        JobSkill.objects.get_or_create(
            job_role=self.job, skill=self.python,
            defaults={'importance_weight': 5, 'is_fundamental': True}
        )
        JobSkill.objects.get_or_create(
            job_role=self.job, skill=self.django_skill,
            defaults={'importance_weight': 4}
        )

        StudentSkill.objects.create(student=self.alice, skill=self.python, level='intermediate')
        Resume.objects.create(
            student=self.alice,
            extracted_text="TOP_SECRET_RESUME_TEXT_FOR_TESTING with private info"
        )

        self.analysis = run_analysis(self.alice, self.job)
        generate_recommendations(self.analysis)

        self.alice_client = Client()
        self.alice_client.force_login(self.alice)

        self.bob_client = Client()
        self.bob_client.force_login(self.bob)

        self.anon_client = Client()

    def test_valid_link_works_logged_out(self):
        """A valid unexpired, unrevoked share link is accessible to logged-out users."""
        link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            hide_name=True
        )

        response = self.anon_client.get(f'/share/{link.token}/')
        self.assertEqual(response.status_code, 200)

        # Must have noindex meta and no-store cache header
        content = response.content.decode('utf-8')
        self.assertIn('<meta name="robots" content="noindex">', content)
        self.assertEqual(response['Cache-Control'], 'no-store')

        # Must display role title and score
        self.assertIn(self.job.title, content)
        self.assertIn(f"{self.analysis.readiness_score:.0f}<small>%</small>", content)

        # Must display skill statuses and roadmap
        self.assertIn(self.python.name, content)
        self.assertIn(self.django_skill.name, content)

    def test_expired_token_returns_404(self):
        """Accessing an expired token returns 404."""
        link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() - timedelta(hours=1),
            hide_name=True
        )
        response = self.anon_client.get(f'/share/{link.token}/')
        self.assertEqual(response.status_code, 404)

    def test_revoked_token_returns_404(self):
        """Accessing a revoked token returns 404."""
        link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            revoked_at=timezone.now(),
            hide_name=True
        )
        response = self.anon_client.get(f'/share/{link.token}/')
        self.assertEqual(response.status_code, 404)

    def test_unknown_token_returns_404(self):
        """Accessing an unknown/random token returns 404."""
        response = self.anon_client.get('/share/unknown-nonexistent-token-xyz123/')
        self.assertEqual(response.status_code, 404)

    def test_other_users_cannot_create_share_link(self):
        """Another user cannot create a share link for an analysis they do not own."""
        url = reverse('analysis:create_share_link', kwargs={'pk': self.analysis.pk})
        response = self.bob_client.post(url, {'days': 7, 'hide_name': True})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.analysis.share_links.count(), 0)

    def test_other_users_cannot_revoke_share_link(self):
        """Another user cannot revoke a share link for an analysis they do not own."""
        link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            hide_name=True
        )
        url = reverse('analysis:revoke_share_link', kwargs={'pk': link.pk})
        response = self.bob_client.post(url)
        self.assertEqual(response.status_code, 404)

        link.refresh_from_db()
        self.assertIsNone(link.revoked_at)

    def test_owner_can_create_and_revoke_share_link(self):
        """The analysis owner can create and revoke share links successfully."""
        create_url = reverse('analysis:create_share_link', kwargs={'pk': self.analysis.pk})
        response = self.alice_client.post(create_url, {'days': 14, 'hide_name': False})
        self.assertEqual(response.status_code, 302)

        link = self.analysis.share_links.first()
        self.assertIsNotNone(link)
        self.assertFalse(link.hide_name)
        self.assertGreater(link.expires_at, timezone.now() + timedelta(days=13))

        revoke_url = reverse('analysis:revoke_share_link', kwargs={'pk': link.pk})
        response = self.alice_client.post(revoke_url)
        self.assertEqual(response.status_code, 302)

        link.refresh_from_db()
        self.assertIsNotNone(link.revoked_at)

    def test_page_contains_no_resume_text_or_email_or_username(self):
        """Public share page never exposes student resume text, email, or username."""
        link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            hide_name=True
        )

        response = self.anon_client.get(f'/share/{link.token}/')
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertNotIn("TOP_SECRET_RESUME_TEXT_FOR_TESTING", content)
        self.assertNotIn(self.alice.email, content)
        self.assertNotIn(self.alice.username, content)

    def test_hide_name_respected(self):
        """When hide_name is True, Full_name is hidden; when False, Full_name is shown."""
        # 1. With hide_name=True (default)
        link_hidden = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            hide_name=True
        )
        resp_hidden = self.anon_client.get(f'/share/{link_hidden.token}/')
        self.assertEqual(resp_hidden.status_code, 200)
        content_hidden = resp_hidden.content.decode('utf-8')
        self.assertNotIn("Alice TestFullname", content_hidden)

        # 2. With hide_name=False
        link_shown = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            hide_name=False
        )
        resp_shown = self.anon_client.get(f'/share/{link_shown.token}/')
        self.assertEqual(resp_shown.status_code, 200)
        content_shown = resp_shown.content.decode('utf-8')
        self.assertIn("Alice TestFullname", content_shown)

    def test_get_on_create_and_revoke_returns_405(self):
        """GET on create and revoke endpoints returns 405 Method Not Allowed."""
        link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7)
        )
        create_url = reverse('analysis:create_share_link', kwargs={'pk': self.analysis.pk})
        revoke_url = reverse('analysis:revoke_share_link', kwargs={'pk': link.pk})

        resp_create = self.alice_client.get(create_url)
        self.assertEqual(resp_create.status_code, 405)

        resp_revoke = self.alice_client.get(revoke_url)
        self.assertEqual(resp_revoke.status_code, 405)

    def test_analysis_pk_not_in_share_link(self):
        """The analysis PK must never be present in the public share link."""
        link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7)
        )
        url = reverse('public_share', kwargs={'token': link.token})
        self.assertNotIn(str(self.analysis.pk), url)
        self.assertEqual(url, f'/share/{link.token}/')

    def test_report_page_lists_active_links_with_copy_and_revoke(self):
        """The owner's report page lists active share links with Copy and Revoke buttons."""
        active_link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            hide_name=True
        )
        revoked_link = ShareLink.objects.create(
            analysis=self.analysis,
            expires_at=timezone.now() + timedelta(days=7),
            revoked_at=timezone.now()
        )

        report_url = reverse('analysis:report', kwargs={'pk': self.analysis.pk})
        response = self.alice_client.get(report_url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        # Active link token and revoke form are shown
        self.assertIn(active_link.token, content)
        self.assertIn(reverse('analysis:revoke_share_link', kwargs={'pk': active_link.pk}), content)
        self.assertIn("Copy", content)
        self.assertIn("Revoke", content)

        # Revoked link token is NOT shown in active links
        self.assertNotIn(revoked_link.token, content)
