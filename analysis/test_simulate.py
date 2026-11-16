"""
analysis/test_simulate.py
Tests for the "What if I learn this?" Simulator feature.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from skills.models import Skill, StudentSkill
from jobs.models import JobRole, JobSkill
from projects.models import Project, ProjectSkill
from analysis.models import SkillAnalysis, SkillGap
from analysis.services.gap_engine import run_analysis
from analysis.services.simulate import simulate_score


class SimulatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='password123')
        self.other_user = User.objects.create_user('bob', password='password123')

        self.python, _ = Skill.objects.get_or_create(name='Python')
        self.django_skill, _ = Skill.objects.get_or_create(name='Django')
        self.docker, _ = Skill.objects.get_or_create(name='Docker')
        self.sql, _ = Skill.objects.get_or_create(name='SQL')

        self.job, _ = JobRole.objects.get_or_create(title='Backend Developer')
        JobSkill.objects.get_or_create(
            job_role=self.job, skill=self.python,
            defaults={'importance_weight': 5, 'is_fundamental': True}
        )
        JobSkill.objects.get_or_create(
            job_role=self.job, skill=self.django_skill,
            defaults={'importance_weight': 4}
        )
        JobSkill.objects.get_or_create(
            job_role=self.job, skill=self.docker,
            defaults={'importance_weight': 3}
        )
        JobSkill.objects.get_or_create(
            job_role=self.job, skill=self.sql,
            defaults={'importance_weight': 2}
        )

        # Alice starts with Python demonstrated via declared + project
        StudentSkill.objects.create(student=self.user, skill=self.python, level='intermediate')
        proj = Project.objects.create(student=self.user, name='Web API')
        ProjectSkill.objects.create(project=proj, skill=self.python)

        self.analysis = run_analysis(self.user, self.job)
        self.client = Client()
        self.client.force_login(self.user)

    def test_projected_is_never_below_current(self):
        """Projected score must never drop below current analysis score for any input."""
        current = self.analysis.readiness_score
        test_inputs = [
            [],
            [self.django_skill.id],
            [self.docker.id],
            [self.django_skill.id, self.docker.id],
            [99999],
            [-1, 0, 'invalid'],
            [self.python.id],  # already covered skill
        ]
        url = reverse('analysis:simulate', kwargs={'pk': self.analysis.pk})

        for ids in test_inputs:
            # Test direct service function
            score = simulate_score(self.analysis, ids)
            self.assertGreaterEqual(
                score, current,
                f"simulate_score projected {score} which is below current {current} for input {ids}"
            )

            # Test JSON endpoint
            response = self.client.post(
                url,
                data=json.dumps({'skill_ids': ids}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertGreaterEqual(
                data['projected'], data['current'],
                f"API projected {data['projected']} below current {data['current']} for input {ids}"
            )
            self.assertGreaterEqual(data['gain'], 0.0)

    def test_ticking_nothing_gives_gain_zero(self):
        """Ticking nothing or sending empty list returns gain 0 and projected == current."""
        url = reverse('analysis:simulate', kwargs={'pk': self.analysis.pk})
        response = self.client.post(
            url,
            data=json.dumps({'skill_ids': []}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['current'], round(float(self.analysis.readiness_score), 1))
        self.assertEqual(data['projected'], round(float(self.analysis.readiness_score), 1))
        self.assertEqual(data['gain'], 0.0)

    def test_ticking_all_gaps_gives_the_maximum(self):
        """Ticking all gaps achieves 100% readiness and maximum gain."""
        all_gap_ids = list(self.analysis.gaps.values_list('skill_id', flat=True))
        url = reverse('analysis:simulate', kwargs={'pk': self.analysis.pk})
        response = self.client.post(
            url,
            data=json.dumps({'skill_ids': all_gap_ids}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['projected'], 100.0)
        expected_gain = round(100.0 - round(float(self.analysis.readiness_score), 1), 1)
        self.assertEqual(data['gain'], expected_gain)

    def test_other_users_analyses_return_404(self):
        """Accessing another user's analysis returns 404 (student data isolation)."""
        bob_analysis = run_analysis(self.other_user, self.job)
        url = reverse('analysis:simulate', kwargs={'pk': bob_analysis.pk})

        response = self.client.post(
            url,
            data=json.dumps({'skill_ids': [self.django_skill.id]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)

    def test_get_returns_405(self):
        """GET request to the simulate endpoint is forbidden with 405 Method Not Allowed."""
        url = reverse('analysis:simulate', kwargs={'pk': self.analysis.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_no_rows_are_written(self):
        """Simulation never creates, updates, or deletes any database rows."""
        analysis_count_before = SkillAnalysis.objects.count()
        gap_count_before = SkillGap.objects.count()
        skill_count_before = Skill.objects.count()
        initial_score = self.analysis.readiness_score

        url = reverse('analysis:simulate', kwargs={'pk': self.analysis.pk})
        response = self.client.post(
            url,
            data=json.dumps({'skill_ids': [self.django_skill.id, self.docker.id]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # Database rows must be unchanged
        self.assertEqual(SkillAnalysis.objects.count(), analysis_count_before)
        self.assertEqual(SkillGap.objects.count(), gap_count_before)
        self.assertEqual(Skill.objects.count(), skill_count_before)

        # Analysis instance must remain unmodified
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.readiness_score, initial_score)

    def test_ignore_ids_that_are_not_gaps_of_analysis(self):
        """IDs of skills not required by this job role are ignored."""
        unrelated_skill, _ = Skill.objects.get_or_create(name='Photoshop')
        url = reverse('analysis:simulate', kwargs={'pk': self.analysis.pk})

        response = self.client.post(
            url,
            data=json.dumps({'skill_ids': [unrelated_skill.id, 999999]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['current'], round(float(self.analysis.readiness_score), 1))
        self.assertEqual(data['projected'], round(float(self.analysis.readiness_score), 1))
        self.assertEqual(data['gain'], 0.0)

    def test_anonymous_user_redirected(self):
        """Unauthenticated requests are redirected to the login page."""
        anon_client = Client()
        url = reverse('analysis:simulate', kwargs={'pk': self.analysis.pk})
        response = anon_client.post(
            url,
            data=json.dumps({'skill_ids': [self.django_skill.id]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_report_template_supports_no_js_and_contains_simulator_markup(self):
        """The report page includes the simulator markup hidden with d-none so it works without JS."""
        url = reverse('analysis:report', kwargs={'pk': self.analysis.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        # Simulator panel is rendered with class d-none
        self.assertIn('id="simulator-panel"', content)
        self.assertIn('simulator-card mb-4 d-none', content)

        # Checkbox wrappers have d-none
        self.assertIn('simulator-checkbox-wrapper d-none', content)

        # Checkbox rendered for non-covered skill (Django)
        self.assertIn(f'id="simulate-skill-{self.django_skill.id}"', content)

        # Checkbox is NOT rendered for demonstrated skill (Python)
        self.assertNotIn(f'id="simulate-skill-{self.python.id}"', content)

