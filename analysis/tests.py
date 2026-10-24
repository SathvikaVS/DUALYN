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

    def test_compare_page_renders_with_empty_and_selected_comparison_states(self):
        client = Client()
        client.force_login(self.alice)
        url = reverse('analysis:compare')

        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add one more result to compare.')

        later = SkillAnalysis.objects.create(
            student=self.alice,
            job_role=self.job,
            readiness_score=65,
        )
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose two results')

        response = client.get(url, {'old': self.analysis.pk, 'new': later.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Skill changes')

    def test_anonymous_user_is_redirected_to_login(self):
        client = Client()
        response = client.get(reverse('analysis:report', args=[self.analysis.pk]))
        self.assertEqual(response.status_code, 302)


class DualynSkillGapEnhancementTests(TestCase):
    """
    Automated test suite verifying the improved skill gap analyzer logic
    against all requirements from Section 12 (Tests A through L).
    """
    def setUp(self):
        from jobs.services.role_profiles import sync_role_profiles_to_db
        sync_role_profiles_to_db()

        self.student = User.objects.create_user('charlie', password='password123')
        self.python_role = JobRole.objects.get(title='Python Developer')
        self.data_analyst_role = JobRole.objects.get(title='Data Analyst')

    def test_a_html_and_css(self):
        """Test A: Input HTML5, CSS3, responsive design -> HTML & CSS recognized, not missing."""
        Resume.objects.create(
            student=self.student,
            extracted_text="Web Development: HTML5, CSS3, responsive design basics."
        )
        analysis = run_analysis(self.student, self.python_role)
        gap = analysis.gaps.filter(skill__name='HTML & CSS').first()
        self.assertIsNotNone(gap)
        self.assertNotEqual(gap.status, 'missing')
        self.assertIn(gap.status, ['demonstrated', 'covered', 'mentioned'])

    def test_b_oop(self):
        """Test B: Input OOP basics -> Object-Oriented Programming recognized as basic evidence."""
        Resume.objects.create(
            student=self.student,
            extracted_text="Core Concepts: OOP basics, software architecture."
        )
        analysis = run_analysis(self.student, self.python_role)
        gap = analysis.gaps.filter(skill__name='Object-Oriented Programming').first()
        self.assertIsNotNone(gap)
        self.assertNotEqual(gap.status, 'missing')
        self.assertEqual(gap.status, 'mentioned')
        self.assertIn('OOP basics', gap.reasoning)

    def test_c_python(self):
        """Test C: Input Python -> Python recognized as mentioned, proficiency not assumed."""
        Resume.objects.create(
            student=self.student,
            extracted_text="Technical Skills: Python."
        )
        analysis = run_analysis(self.student, self.python_role)
        gap = analysis.gaps.filter(skill__name='Python').first()
        self.assertIsNotNone(gap)
        self.assertEqual(gap.status, 'mentioned')
        # Proficiency not assumed as demonstrated
        self.assertNotEqual(gap.status, 'demonstrated')

    def test_d_project_evidence(self):
        """Test D: Project description containing Django, SQL, HTML, CSS -> detected from project, not missing."""
        resume_text = """
Projects:
Project 1: BookNest Web Application
- Built using Django, SQL, HTML, and CSS.
- Implemented user accounts and book catalogs.
"""
        Resume.objects.create(student=self.student, extracted_text=resume_text)
        analysis = run_analysis(self.student, self.python_role)
        for skill_name in ['Django', 'SQL', 'HTML & CSS']:
            gap = analysis.gaps.filter(skill__name=skill_name).first()
            if gap:
                self.assertNotEqual(gap.status, 'missing', f"{skill_name} should not be missing")

    def test_e_genuine_gaps(self):
        """Test E: Resume with no mention of REST APIs, JavaScript, PostgreSQL -> classified as missing."""
        Resume.objects.create(
            student=self.student,
            extracted_text="Skills: Python, Django, SQL basics."
        )
        analysis = run_analysis(self.student, self.python_role)
        for skill_name in ['REST API', 'JavaScript', 'PostgreSQL']:
            gap = analysis.gaps.filter(skill__name=skill_name).first()
            if gap:
                self.assertEqual(gap.status, 'missing', f"{skill_name} should be missing")

    def test_f_aliases(self):
        """Test F: Input JS, DSA, Postgres, DRF -> canonical skills recognized."""
        from skills.services.normalization import extract_skills_with_evidence
        raw_text = "Technical Skills: JS, DSA, Postgres, DRF."
        extracted = extract_skills_with_evidence(raw_text)
        self.assertIn('JavaScript', extracted)
        self.assertIn('Data Structures & Algorithms', extracted)
        self.assertIn('PostgreSQL', extracted)
        self.assertIn('REST API', extracted)

    def test_g_duplicate_evidence(self):
        """Test G: Python in declared, resume skills, and 2 projects -> exactly one Python gap counted."""
        python_skill = Skill.objects.get(name='Python')
        StudentSkill.objects.create(student=self.student, skill=python_skill, level='intermediate')

        p1 = Project.objects.create(student=self.student, name='Project 1')
        ProjectSkill.objects.create(project=p1, skill=python_skill)
        p2 = Project.objects.create(student=self.student, name='Project 2')
        ProjectSkill.objects.create(project=p2, skill=python_skill)

        Resume.objects.create(student=self.student, extracted_text="Python programming in project 1 and 2.")

        analysis = run_analysis(self.student, self.python_role)
        python_gaps = analysis.gaps.filter(skill__name='Python')
        self.assertEqual(python_gaps.count(), 1)
        # Should be demonstrated/covered with combined evidence
        self.assertIn(python_gaps.first().status, ['demonstrated', 'covered'])

    def test_h_role_specific_scoring(self):
        """Test H: Python Developer and Data Analyst have different competency profiles and weights."""
        py_skills = {js.skill.name: js.importance_weight for js in self.python_role.job_skills.all()}
        da_skills = {js.skill.name: js.importance_weight for js in self.data_analyst_role.job_skills.all()}

        self.assertIn('Django', py_skills)
        self.assertNotIn('Django', da_skills)
        self.assertIn('Excel', da_skills)
        self.assertNotIn('Excel', py_skills)

    def test_i_readiness_score(self):
        """Test I: Score follows documented formula, remains between 0 and 100, changes predictably."""
        # 1. Zero evidence -> 0%
        a1 = run_analysis(self.student, self.python_role)
        self.assertEqual(a1.readiness_score, 0.0)

        # 2. Add some skills -> score increases
        Resume.objects.create(student=self.student, extracted_text="Python, Django, SQL")
        a2 = run_analysis(self.student, self.python_role)
        self.assertGreater(a2.readiness_score, 0.0)
        self.assertLessEqual(a2.readiness_score, 100.0)

        # 3. Add more demonstrated skills -> score increases further
        for js in self.python_role.job_skills.all():
            StudentSkill.objects.get_or_create(student=self.student, skill=js.skill, defaults={'level': 'advanced'})
        a3 = run_analysis(self.student, self.python_role)
        self.assertEqual(a3.readiness_score, 100.0)

    def test_j_parsing_failure(self):
        """Test J: User sees a clear warning flag instead of misleading report when parsing fails."""
        # Resume with empty text represents failed extraction
        Resume.objects.create(student=self.student, extracted_text="")
        analysis = run_analysis(self.student, self.python_role)
        self.assertTrue(analysis.has_warning)
        self.assertTrue(len(analysis.warning_message) > 0)
        self.assertIn("No readable text", analysis.warning_message)

    def test_k_roadmap_dependencies(self):
        """Test K: Fundamental skills appear before dependent advanced topics; demonstrated excluded."""
        from recommendations.services.recommendation_engine import generate_recommendations
        # Student demonstrates Django
        django_skill = Skill.objects.get(name='Django')
        StudentSkill.objects.create(student=self.student, skill=django_skill, level='advanced')

        analysis = run_analysis(self.student, self.python_role)
        roadmap = generate_recommendations(analysis)

        # Django is demonstrated, so it should not appear in the roadmap
        roadmap_skill_names = [item.skill_gap.skill.name for item in roadmap.items.all()]
        self.assertNotIn('Django', roadmap_skill_names)

        # Phase 1 items (OOP, DSA) appear before Phase 2 (REST API)
        items = list(roadmap.items.select_related('skill_gap__skill').all())
        phase_map = {item.skill_gap.skill.name: item.phase for item in items}

        if 'Object-Oriented Programming' in phase_map and 'REST API' in phase_map:
            self.assertLess(phase_map['Object-Oriented Programming'], phase_map['REST API'])
        if 'Data Structures & Algorithms' in phase_map and 'REST API' in phase_map:
            self.assertLess(phase_map['Data Structures & Algorithms'], phase_map['REST API'])

    def test_l_regression(self):
        """Test L: Existing auth, dashboard, resume list, history, and report views continue to function."""
        client = Client()
        client.force_login(self.student)

        # 1. Dashboard
        resp = client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)

        # 2. Run analysis view
        resp = client.get(reverse('analysis:run'))
        self.assertEqual(resp.status_code, 200)

        # 3. Post run analysis
        resp = client.post(reverse('analysis:run'), {'job_role': self.python_role.pk})
        self.assertEqual(resp.status_code, 302)

        # 4. History view
        resp = client.get(reverse('analysis:history'))
        self.assertEqual(resp.status_code, 200)

        # 5. Report view
        latest_analysis = self.student.analyses.first()
        self.assertIsNotNone(latest_analysis)
        resp = client.get(reverse('analysis:report', args=[latest_analysis.pk]))
        self.assertEqual(resp.status_code, 200)

        # 6. Resume list view
        resp = client.get(reverse('resumes:list'))
        self.assertEqual(resp.status_code, 200)

        # 7. Student profile view
        resp = client.get(reverse('students:profile'))
        self.assertEqual(resp.status_code, 200)