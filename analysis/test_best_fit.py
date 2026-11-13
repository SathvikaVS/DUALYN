import tempfile
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import UserRole
from skills.models import Skill, StudentSkill
from jobs.models import JobRole, JobSkill
from projects.models import Project, ProjectSkill
from resumes.models import Resume
from analysis.models import SkillAnalysis, SkillGap
from analysis.services.gap_engine import run_analysis
from analysis.services.best_fit import rank_roles_for


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class BestFitRolesTests(TestCase):
    def setUp(self):
        # Skills
        self.python, _ = Skill.objects.get_or_create(name='Python')
        self.django_skill, _ = Skill.objects.get_or_create(name='Django')
        self.docker, _ = Skill.objects.get_or_create(name='Docker')
        self.sql, _ = Skill.objects.get_or_create(name='SQL')
        self.figma, _ = Skill.objects.get_or_create(name='Figma')

        # Roles
        self.backend_role, _ = JobRole.objects.get_or_create(title='Backend Engineer')
        JobSkill.objects.get_or_create(job_role=self.backend_role, skill=self.python, defaults={'importance_weight': 5, 'is_fundamental': True})
        JobSkill.objects.get_or_create(job_role=self.backend_role, skill=self.django_skill, defaults={'importance_weight': 4})
        JobSkill.objects.get_or_create(job_role=self.backend_role, skill=self.docker, defaults={'importance_weight': 3})

        self.data_role, _ = JobRole.objects.get_or_create(title='Data Analyst')
        JobSkill.objects.get_or_create(job_role=self.data_role, skill=self.python, defaults={'importance_weight': 4})
        JobSkill.objects.get_or_create(job_role=self.data_role, skill=self.sql, defaults={'importance_weight': 5, 'is_fundamental': True})

        self.design_role, _ = JobRole.objects.get_or_create(title='UI Designer')
        JobSkill.objects.get_or_create(job_role=self.design_role, skill=self.figma, defaults={'importance_weight': 5, 'is_fundamental': True})

        self.empty_role, _ = JobRole.objects.get_or_create(title='Empty Role Without Skills')

        # Student 1: Python and Django proficient
        self.student1 = User.objects.create_user('alice', password='password123')
        UserRole.objects.get_or_create(user=self.student1, defaults={'role': UserRole.STUDENT})
        StudentSkill.objects.create(student=self.student1, skill=self.python, level='advanced')
        StudentSkill.objects.create(student=self.student1, skill=self.django_skill, level='intermediate')

        project = Project.objects.create(student=self.student1, name='Web API')
        ProjectSkill.objects.create(project=project, skill=self.python)

        resume_file = SimpleUploadedFile('alice_cv.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        resume = Resume.objects.create(
            student=self.student1,
            file=resume_file,
            extracted_text="Python Django backend developer."
        )
        resume.ai_extracted_skills.set([self.python, self.django_skill])

        # Student 2: Design only
        self.student2 = User.objects.create_user('bob', password='password123')
        UserRole.objects.get_or_create(user=self.student2, defaults={'role': UserRole.STUDENT})
        StudentSkill.objects.create(student=self.student2, skill=self.figma, level='advanced')

        # Student 3: No evidence at all
        self.student3 = User.objects.create_user('charlie', password='password123')
        UserRole.objects.get_or_create(user=self.student3, defaults={'role': UserRole.STUDENT})

        self.client = Client()

    def test_scores_equal_run_analysis_for_same_student_and_role(self):
        ranked = rank_roles_for(self.student1)
        self.assertGreater(len(ranked), 0)

        for item in ranked:
            role = item['role']
            # Run the persisted analysis
            analysis = run_analysis(self.student1, role)
            self.assertEqual(
                item['score'],
                analysis.readiness_score,
                f"Mismatch for role {role.title}: rank_roles_for score {item['score']} != run_analysis {analysis.readiness_score}"
            )
            covered_in_db = analysis.gaps.filter(status__in=['covered', 'demonstrated']).count()
            self.assertEqual(item['covered_count'], covered_in_db)
            missing_in_db = analysis.gaps.filter(status='missing').count()
            self.assertEqual(item['missing_count'], missing_in_db)

    def test_viewing_page_creates_no_skillanalysis_rows(self):
        self.client.force_login(self.student1)
        initial_analysis_count = SkillAnalysis.objects.count()
        initial_gap_count = SkillGap.objects.count()

        url = reverse('analysis:best_fit')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SkillAnalysis.objects.count(), initial_analysis_count)
        self.assertEqual(SkillGap.objects.count(), initial_gap_count)

    def test_ordering_sorted_by_score_descending(self):
        ranked = rank_roles_for(self.student1)
        scores = [item['score'] for item in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Alice should rank Backend Engineer higher than UI Designer (0%)
        role_titles = [item['role'].title for item in ranked]
        self.assertIn('Backend Engineer', role_titles)
        self.assertIn('UI Designer', role_titles)
        self.assertLess(role_titles.index('Backend Engineer'), role_titles.index('UI Designer'))

        # Also verify in template response
        self.client.force_login(self.student1)
        response = self.client.get(reverse('analysis:best_fit'))
        content = response.content.decode('utf-8')
        pos_backend = content.find('Backend Engineer')
        pos_designer = content.find('UI Designer')
        self.assertTrue(pos_backend < pos_designer)

    def test_roles_with_no_job_skills_are_skipped(self):
        ranked = rank_roles_for(self.student1)
        ranked_role_ids = [item['role'].id for item in ranked]
        self.assertNotIn(self.empty_role.id, ranked_role_ids)

    def test_student_with_no_evidence_still_renders(self):
        self.client.force_login(self.student3)
        response = self.client.get(reverse('analysis:best_fit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Best-fit roles")
        # All roles should have 0% score
        ranked = response.context['ranked_roles']
        self.assertTrue(all(item['score'] == 0.0 for item in ranked))
        self.assertTrue(all(item['covered_count'] == 0 for item in ranked))

    def test_anonymous_users_are_redirected(self):
        response = self.client.get(reverse('analysis:best_fit'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_two_students_data_isolation(self):
        # Alice's ranking
        alice_ranked = rank_roles_for(self.student1)
        alice_scores = {r['role'].title: r['score'] for r in alice_ranked}

        # Bob's ranking
        bob_ranked = rank_roles_for(self.student2)
        bob_scores = {r['role'].title: r['score'] for r in bob_ranked}

        # Alice has high backend score, 0 design
        self.assertGreater(alice_scores['Backend Engineer'], 50)
        self.assertEqual(alice_scores['UI Designer'], 0.0)

        # Bob has high design score, 0 backend
        self.assertEqual(bob_scores['Backend Engineer'], 0.0)
        self.assertGreater(bob_scores['UI Designer'], 50)

        # Verify Bob cannot see Alice's scores when logged in
        self.client.force_login(self.student2)
        response = self.client.get(reverse('analysis:best_fit'))
        self.assertEqual(response.status_code, 200)
        bob_page_scores = {r['role'].title: r['score'] for r in response.context['ranked_roles']}
        self.assertEqual(bob_page_scores, bob_scores)

    def test_top_gaps_selection_and_attributes(self):
        ranked = rank_roles_for(self.student1)
        backend_item = next(r for r in ranked if r['role'] == self.backend_role)
        # Alice is missing Docker for Backend Engineer
        self.assertLessEqual(len(backend_item['top_gaps']), 3)
        gap_skill_names = [g.skill.name for g in backend_item['top_gaps']]
        self.assertIn('Docker', gap_skill_names)
        # Verify both dict and attribute access work
        gap = backend_item['top_gaps'][0]
        self.assertEqual(gap.skill.name, gap['skill'].name)
        self.assertEqual(gap.status, gap['status'])
        self.assertEqual(gap.priority, gap['priority'])

    def test_run_full_check_form_on_card(self):
        self.client.force_login(self.student1)
        response = self.client.get(reverse('analysis:best_fit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Run full check')
        self.assertContains(response, f'value="{self.backend_role.pk}"')

        # Submitting the form creates a new analysis snapshot
        post_response = self.client.post(reverse('analysis:run'), {
            'job_role': self.backend_role.pk,
        })
        self.assertEqual(post_response.status_code, 302)
        latest_analysis = SkillAnalysis.objects.filter(
            student=self.student1,
            job_role=self.backend_role
        ).first()
        self.assertIsNotNone(latest_analysis)
        self.assertRedirects(post_response, reverse('analysis:report', kwargs={'pk': latest_analysis.pk}))

    def test_no_n_plus_one_queries(self):
        # Create additional roles and skills to verify queries stay constant
        for i in range(5):
            extra_role = JobRole.objects.create(title=f'Extra Role {i}')
            JobSkill.objects.create(job_role=extra_role, skill=self.python, importance_weight=3)

        # Count queries when running rank_roles_for
        with self.assertNumQueries(6):
            # 1: declared skills
            # 2: project skills
            # 3: latest resume
            # 4: ai_extracted_skills values_list
            # 5: JobRole.objects.all()
            # 6: JobSkill.objects.select_related('skill').all()
            rank_roles_for(self.student1)

