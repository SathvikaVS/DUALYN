"""
analysis/test_unproven.py
Tests for the "Skills you list but haven't shown yet" (unproven claims) service and UI.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from skills.models import Skill, StudentSkill
from jobs.models import JobRole, JobSkill
from projects.models import Project, ProjectSkill
from resumes.models import Resume
from analysis.models import SkillAnalysis, SkillGap
from analysis.services.gap_engine import run_analysis
from analysis.services.unproven import unproven_claims, DEFAULT_PROJECT_IDEA
from recommendations.services.recommendation_engine import generate_recommendations


class UnprovenClaimsTests(TestCase):
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

        self.client = Client()
        self.client.force_login(self.user)

    def test_claimed_skill_with_project_is_excluded(self):
        """A skill claimed and backed by a student project is excluded from unproven claims."""
        # Alice declares Python and has a Project tagged with Python
        StudentSkill.objects.create(student=self.user, skill=self.python, level='intermediate')
        proj = Project.objects.create(student=self.user, name='Python Script')
        ProjectSkill.objects.create(project=proj, skill=self.python)

        analysis = run_analysis(self.user, self.job)
        claims = unproven_claims(analysis)
        claimed_skill_ids = [c['skill'].id for c in claims]

        self.assertNotIn(
            self.python.id, claimed_skill_ids,
            "Python has a ProjectSkill and must be excluded from unproven claims."
        )

    def test_claimed_skill_without_project_is_included(self):
        """A skill declared on student profile with no ProjectSkill is included."""
        # Alice declares Django, but has NO project for it
        StudentSkill.objects.create(student=self.user, skill=self.django_skill, level='intermediate')

        analysis = run_analysis(self.user, self.job)
        claims = unproven_claims(analysis)
        claimed_skills = {c['skill'].id: c for c in claims}

        self.assertIn(
            self.django_skill.id, claimed_skills,
            "Django is declared without a project and must be included in unproven claims."
        )
        claim = claimed_skills[self.django_skill.id]
        self.assertIn('Declared', claim['claimed_via'])
        self.assertTrue(bool(claim['project_idea']))

    def test_resume_only_claims_are_included(self):
        """A skill found only in the student's resume with no project is included."""
        # Alice has Docker in her resume (via AI extracted skills), not declared in StudentSkill
        resume = Resume.objects.create(
            student=self.user,
            extracted_text="Experienced with containerization tools in production deployments."
        )
        resume.ai_extracted_skills.set([self.docker])

        analysis = run_analysis(self.user, self.job)
        claims = unproven_claims(analysis)
        claimed_skills = {c['skill'].id: c for c in claims}

        self.assertIn(
            self.docker.id, claimed_skills,
            "Docker is in resume without a project and must be included in unproven claims."
        )
        claim = claimed_skills[self.docker.id]
        self.assertIn('Resume', claim['claimed_via'])

    def test_skill_nobody_claimed_is_excluded(self):
        """A job requirement that the student never declared or mentioned is excluded."""
        # SQL is required by the role, but Alice never declared it, has no resume, no projects
        analysis = run_analysis(self.user, self.job)
        claims = unproven_claims(analysis)
        claimed_skill_ids = [c['skill'].id for c in claims]

        self.assertNotIn(
            self.sql.id, claimed_skill_ids,
            "SQL was never claimed by the student and must be excluded from unproven claims."
        )

    def test_other_users_data_never_leaks(self):
        """Projects or claims from another student do not leak or affect unproven claims."""
        # Alice declares Django without a project
        StudentSkill.objects.create(student=self.user, skill=self.django_skill, level='intermediate')

        # Bob has a project with Django
        bob_proj = Project.objects.create(student=self.other_user, name="Bob's Django App")
        ProjectSkill.objects.create(project=bob_proj, skill=self.django_skill)

        # Alice's analysis must STILL show Django as unproven
        alice_analysis = run_analysis(self.user, self.job)
        alice_claims = unproven_claims(alice_analysis)
        alice_claim_ids = [c['skill'].id for c in alice_claims]
        self.assertIn(
            self.django_skill.id, alice_claim_ids,
            "Bob's project must not prove Alice's declared Django claim."
        )

        # Bob has NOT declared Django
        bob_analysis = run_analysis(self.other_user, self.job)
        bob_claims = unproven_claims(bob_analysis)
        bob_claim_ids = [c['skill'].id for c in bob_claims]
        self.assertNotIn(
            self.django_skill.id, bob_claim_ids,
            "Bob has a project for Django, so it must not be in Bob's unproven claims."
        )

    def test_scores_unchanged(self):
        """Calling unproven_claims is a pure function that never changes scores or writes rows."""
        StudentSkill.objects.create(student=self.user, skill=self.django_skill, level='intermediate')
        analysis = run_analysis(self.user, self.job)
        initial_score = analysis.readiness_score

        count_analyses_before = SkillAnalysis.objects.count()
        count_gaps_before = SkillGap.objects.count()

        # Run unproven_claims multiple times
        claims1 = unproven_claims(analysis)
        claims2 = unproven_claims(analysis)
        self.assertEqual(len(claims1), len(claims2))

        # Check DB counts and score
        self.assertEqual(SkillAnalysis.objects.count(), count_analyses_before)
        self.assertEqual(SkillGap.objects.count(), count_gaps_before)

        analysis.refresh_from_db()
        self.assertEqual(analysis.readiness_score, initial_score)

    def test_project_idea_comes_from_matching_roadmap_item(self):
        """If a matching RoadmapItem with task_idea exists, it is used as project_idea."""
        StudentSkill.objects.create(student=self.user, skill=self.django_skill, level='intermediate')
        analysis = run_analysis(self.user, self.job)
        generate_recommendations(analysis)

        # Update the task_idea for the Django gap
        django_gap = analysis.gaps.get(skill=self.django_skill)
        roadmap_item = analysis.roadmap.items.filter(skill_gap=django_gap).first()
        if roadmap_item:
            roadmap_item.task_idea = "Build a multi-tenant blog platform with Django"
            roadmap_item.save()

            claims = unproven_claims(analysis)
            claimed_dict = {c['skill'].id: c for c in claims}
            self.assertEqual(
                claimed_dict[self.django_skill.id]['project_idea'],
                "Build a multi-tenant blog platform with Django"
            )

    def test_project_idea_fallback_text_when_no_roadmap_item(self):
        """If no matching RoadmapItem exists, a constant fallback text is used."""
        StudentSkill.objects.create(student=self.user, skill=self.django_skill, level='intermediate')
        analysis = run_analysis(self.user, self.job)
        # No roadmap generated
        claims = unproven_claims(analysis)
        claimed_dict = {c['skill'].id: c for c in claims}
        self.assertEqual(
            claimed_dict[self.django_skill.id]['project_idea'],
            DEFAULT_PROJECT_IDEA
        )

    def test_report_page_renders_unproven_section_and_add_project_link(self):
        """Report view renders the section with add-project link when unproven claims exist."""
        StudentSkill.objects.create(student=self.user, skill=self.django_skill, level='intermediate')
        analysis = run_analysis(self.user, self.job)

        url = reverse('analysis:report', kwargs={'pk': analysis.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertIn("Skills you list but haven't shown yet", content)
        self.assertIn(reverse('admin:projects_project_add'), content)
        self.assertIn(self.django_skill.name, content)

    def test_report_page_hides_unproven_section_when_empty(self):
        """Report view hides the unproven section when there are no unproven claims."""
        # Alice has only Python, and has a project for it
        StudentSkill.objects.create(student=self.user, skill=self.python, level='intermediate')
        proj = Project.objects.create(student=self.user, name='Python Script')
        ProjectSkill.objects.create(project=proj, skill=self.python)

        analysis = run_analysis(self.user, self.job)

        url = reverse('analysis:report', kwargs={'pk': analysis.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertNotIn("Skills you list but haven't shown yet", content)
        self.assertNotIn(reverse('admin:projects_project_add'), content)
