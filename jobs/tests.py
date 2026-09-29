from django.test import TestCase
from skills.models import Skill
from .models import JobRole, JobSkill


class JobSkillTests(TestCase):
    def test_same_skill_cannot_be_required_twice_for_one_job(self):
        job = JobRole.objects.create(title='Data Scientist')
        skill = Skill.objects.create(name='SQL')
        JobSkill.objects.create(job_role=job, skill=skill, importance_weight=3)
        with self.assertRaises(Exception):
            JobSkill.objects.create(job_role=job, skill=skill, importance_weight=5)

    def test_importance_weight_is_stored_correctly(self):
        job = JobRole.objects.create(title='ML Engineer')
        skill = Skill.objects.create(name='TensorFlow')
        js = JobSkill.objects.create(job_role=job, skill=skill, importance_weight=5, is_fundamental=True)
        self.assertEqual(js.importance_weight, 5)
        self.assertTrue(js.is_fundamental)