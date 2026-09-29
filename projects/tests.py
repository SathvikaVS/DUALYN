from django.test import TestCase
from django.contrib.auth.models import User
from skills.models import Skill
from .models import Project, ProjectSkill


class ProjectModelTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user('carol', password='pass12345')
        self.skill = Skill.objects.create(name='Django')

    def test_project_can_be_tagged_with_a_skill(self):
        project = Project.objects.create(student=self.student, name='Portfolio Site')
        ProjectSkill.objects.create(project=project, skill=self.skill)
        self.assertEqual(project.project_skills.count(), 1)

    def test_same_skill_cannot_be_tagged_twice_on_one_project(self):
        project = Project.objects.create(student=self.student, name='Portfolio Site')
        ProjectSkill.objects.create(project=project, skill=self.skill)
        with self.assertRaises(Exception):
            ProjectSkill.objects.create(project=project, skill=self.skill)
