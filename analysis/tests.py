from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from skills.models import Skill, StudentSkill
from jobs.models import JobRole, JobSkill
from projects.models import Project, ProjectSkill
from resumes.models import Resume
from .models import SkillAnalysis, SkillGap
from .services.gap_engine import run_analysis
from .services.progress import compare_analyses


class GapEngineTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user('alice', password='pass12345')
        self.python = Skill.objects.create(name='Python')
        self.django_skill = Skill.objects.create(name='Django')
        self.docker = Skill.objects.create(name='Docker')
        self.job = JobRole.objects.create(title='Python Developer')
        JobSkill.objects.create(job_role=self.job, skill=self.python, importance_weight=5, is_fundamental=True)
        JobSkill.objects.create(job_role=self.job, skill=self.django_skill, importance_weight=4)
        JobSkill.objects.create(job_role=self.job, skill=self.docker, importance_weight=2)

    def test_missing_skill_has_zero_evidence_and_low_score_contribution(self):
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.docker)
        self.assertEqual(gap.status, 'missing')

    def test_declared_intermediate_skill_is_covered(self):
        StudentSkill.objects.create(student=self.student, skill=self.python, level='intermediate')
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.python)
        self.assertEqual(gap.status, 'covered')

    def test_declared_beginner_alone_is_needs_improvement(self):
        StudentSkill.objects.create(student=self.student, skill=self.python, level='beginner')
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.python)
        self.assertEqual(gap.status, 'needs_improvement')

    def test_two_weak_sources_together_count_as_covered(self):
        # beginner declared + used in a project = 2 sources -> covered, even though
        # neither source alone would be enough (Section 12: combined evidence).
        StudentSkill.objects.create(student=self.student, skill=self.python, level='beginner')
        project = Project.objects.create(student=self.student, name='Blog App')
        ProjectSkill.objects.create(project=project, skill=self.python)
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.python)
        self.assertEqual(gap.status, 'covered')

    def test_resume_mention_alone_is_needs_improvement_not_covered(self):
        Resume.objects.create(student=self.student, extracted_text="I have used python for scripting.")
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.python)
        self.assertEqual(gap.status, 'needs_improvement')

    def test_ai_extracted_skill_counts_as_resume_evidence_even_without_literal_mention(self):
        resume = Resume.objects.create(student=self.student, extracted_text="Built web apps using a popular scripting language.")
        resume.ai_extracted_skills.set([self.python])
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.python)
        self.assertEqual(gap.status, 'needs_improvement')
        self.assertIn('mentioned in resume', gap.reasoning)

    def test_missing_fundamental_skill_gets_high_priority(self):
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.python)
        self.assertEqual(gap.priority, 'high')

    def test_covered_skill_never_gets_high_priority(self):
        StudentSkill.objects.create(student=self.student, skill=self.python, level='advanced')
        analysis = run_analysis(self.student, self.job)
        gap = analysis.gaps.get(skill=self.python)
        self.assertEqual(gap.priority, 'low')

    def test_readiness_score_is_weighted_not_flat_average(self):
        # Cover only Python (weight 5 of 5+4+2=11). Flat covered/total would give 33.3%.
        # Weighted must be higher, since Python carries more weight than Django or Docker.
        StudentSkill.objects.create(student=self.student, skill=self.python, level='advanced')
        analysis = run_analysis(self.student, self.job)
        flat_average = round(1 / 3 * 100, 1)
        self.assertGreater(analysis.readiness_score, flat_average)

    def test_full_coverage_gives_100_percent(self):
        for skill in (self.python, self.django_skill, self.docker):
            StudentSkill.objects.create(student=self.student, skill=skill, level='advanced')
        analysis = run_analysis(self.student, self.job)
        self.assertEqual(analysis.readiness_score, 100.0)

    def test_analysis_snapshot_is_not_mutated_by_a_later_run(self):
        first = run_analysis(self.student, self.job)
        first_score = first.readiness_score
        StudentSkill.objects.create(student=self.student, skill=self.python, level='advanced')
        run_analysis(self.student, self.job)
        first.refresh_from_db()
        self.assertEqual(first.readiness_score, first_score)


class ProgressComparisonTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user('bob', password='pass12345')
        self.skill = Skill.objects.create(name='Docker')
        self.job = JobRole.objects.create(title='Backend Developer')
        JobSkill.objects.create(job_role=self.job, skill=self.skill, importance_weight=4)

    def test_improvement_is_detected_between_two_analyses(self):
        old = run_analysis(self.student, self.job)
        StudentSkill.objects.create(student=self.student, skill=self.skill, level='advanced')
        new = run_analysis(self.student, self.job)
        result = compare_analyses(old, new)
        docker_change = next(c for c in result['changes'] if c['skill'] == self.skill)
        self.assertEqual(docker_change['change'], 'improved')
        self.assertGreater(result['score_change'], 0)


class AnalysisPermissionTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice2', password='pass12345')
        self.bob = User.objects.create_user('bob2', password='pass12345')
        self.job = JobRole.objects.create(title='Data Analyst')
        self.analysis = SkillAnalysis.objects.create(student=self.alice, job_role=self.job, readiness_score=50)

    def test_student_cannot_view_another_students_report(self):
        client = Client()
        client.force_login(self.bob)
        response = client.get(reverse('analysis:report', args=[self.analysis.pk]))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_view_their_own_report(self):
        client = Client()
        client.force_login(self.alice)
        response = client.get(reverse('analysis:report', args=[self.analysis.pk]))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self):
        client = Client()
        response = client.get(reverse('analysis:report', args=[self.analysis.pk]))
        self.assertEqual(response.status_code, 302)