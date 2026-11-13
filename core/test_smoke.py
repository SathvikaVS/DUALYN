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
from analysis.services.gap_engine import run_analysis
from recommendations.services.recommendation_engine import generate_recommendations


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class SmokeTests(TestCase):
    def setUp(self):
        self.python, _ = Skill.objects.get_or_create(name='Python')
        self.django_skill, _ = Skill.objects.get_or_create(name='Django')
        self.job, _ = JobRole.objects.get_or_create(title='Python Developer')
        JobSkill.objects.get_or_create(
            job_role=self.job,
            skill=self.python,
            defaults={'importance_weight': 5, 'is_fundamental': True}
        )
        JobSkill.objects.get_or_create(
            job_role=self.job,
            skill=self.django_skill,
            defaults={'importance_weight': 4}
        )

    def _setup_user_with_data(self, username, role, is_staff=False, is_superuser=False):
        if is_superuser:
            user = User.objects.create_superuser(username, f'{username}@example.com', 'pass12345')
        elif is_staff:
            user = User.objects.create_user(username, f'{username}@example.com', 'pass12345', is_staff=True)
        else:
            user = User.objects.create_user(username, f'{username}@example.com', 'pass12345')

        UserRole.objects.get_or_create(user=user, defaults={'role': role, 'is_verified': True})

        resume_file = SimpleUploadedFile(f'{username}_resume.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        resume = Resume.objects.create(
            student=user,
            file=resume_file,
            extracted_text="Python and Django developer with web application experience."
        )
        resume.ai_extracted_skills.set([self.python, self.django_skill])

        student_skill, _ = StudentSkill.objects.get_or_create(
            student=user,
            skill=self.python,
            defaults={'level': 'intermediate'}
        )

        project = Project.objects.create(student=user, name=f'{username} Portfolio Project')
        ProjectSkill.objects.create(project=project, skill=self.python)

        analysis = run_analysis(user, self.job)
        roadmap = generate_recommendations(analysis)

        return {
            'user': user,
            'role': role,
            'resume': resume,
            'skill': student_skill,
            'project': project,
            'analysis': analysis,
            'roadmap': roadmap,
        }

    def _get_read_urls(self, context):
        analysis = context['analysis']
        urls = [
            reverse('dashboard'),
            reverse('accounts:login'),
            reverse('accounts:register'),
            reverse('students:profile'),
            reverse('resumes:list'),
            reverse('resumes:upload'),
            reverse('skills:my_skills'),
            reverse('analysis:best_fit'),
            reverse('analysis:run'),
            reverse('analysis:report', kwargs={'pk': analysis.pk}),
            reverse('analysis:history'),
            reverse('analysis:compare'),
            reverse('feedback:submit'),
            reverse('admin:index'),
        ]
        # Include admin changelists for comprehensive coverage
        admin_changelists = [
            'admin:accounts_userrole_changelist',
            'admin:students_student_profile_changelist',
            'admin:skills_skill_changelist',
            'admin:skills_studentskill_changelist',
            'admin:jobs_jobrole_changelist',
            'admin:resumes_resume_changelist',
            'admin:projects_project_changelist',
            'admin:analysis_skillanalysis_changelist',
            'admin:recommendations_learningroadmap_changelist',
            'admin:recommendations_recommendation_changelist',
            'admin:feedback_feedback_changelist',
        ]
        for name in admin_changelists:
            urls.append(reverse(name))
        return urls

    def _get_state_changing_urls(self, context):
        return [
            reverse('resumes:sync', kwargs={'pk': context['resume'].pk}),
            reverse('skills:sync_resume'),
            reverse('analysis:refresh', kwargs={'pk': context['analysis'].pk}),
            reverse('skills:remove_skill', kwargs={'pk': context['skill'].pk}),
        ]

    def _assert_user_can_get_urls_and_state_changing_are_405(self, context):
        client = Client(raise_request_exception=True)
        client.force_login(context['user'])

        for url in self._get_read_urls(context):
            response = client.get(url)
            self.assertIn(
                response.status_code,
                [200, 302],
                f"URL '{url}' returned status {response.status_code} for user '{context['user'].username}' (role: {context['role']})"
            )

        for url in self._get_state_changing_urls(context):
            response = client.get(url)
            self.assertEqual(
                response.status_code,
                405,
                f"State-changing URL '{url}' should return 405 on GET, but returned {response.status_code} for user '{context['user'].username}'"
            )

    def test_student_smoke(self):
        context = self._setup_user_with_data('smoke_student', UserRole.STUDENT)
        self._assert_user_can_get_urls_and_state_changing_are_405(context)

    def test_company_smoke(self):
        context = self._setup_user_with_data('smoke_company', UserRole.COMPANY)
        self._assert_user_can_get_urls_and_state_changing_are_405(context)

    def test_professor_smoke(self):
        context = self._setup_user_with_data('smoke_professor', UserRole.PROFESSOR)
        self._assert_user_can_get_urls_and_state_changing_are_405(context)

    def test_admin_smoke(self):
        context = self._setup_user_with_data('smoke_admin', UserRole.ADMIN, is_staff=True, is_superuser=True)
        self._assert_user_can_get_urls_and_state_changing_are_405(context)

    def test_anonymous_smoke(self):
        client = Client(raise_request_exception=True)
        public_urls = [
            reverse('dashboard'),
            reverse('accounts:login'),
            reverse('accounts:register'),
        ]
        for url in public_urls:
            response = client.get(url)
            self.assertEqual(response.status_code, 200, f"Public URL '{url}' returned {response.status_code}")

        gated_urls = [
            reverse('students:profile'),
            reverse('resumes:list'),
            reverse('resumes:upload'),
            reverse('skills:my_skills'),
            reverse('analysis:best_fit'),
            reverse('analysis:run'),
            reverse('analysis:history'),
            reverse('feedback:submit'),
        ]
        for url in gated_urls:
            response = client.get(url)
            self.assertEqual(response.status_code, 302, f"Gated URL '{url}' should redirect anonymous user")
