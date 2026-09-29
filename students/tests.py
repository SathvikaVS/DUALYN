from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Student_Profile


class StudentProfileSignalTests(TestCase):
    def test_profile_is_auto_created_when_user_registers(self):
        user = User.objects.create_user('dana', password='pass12345')
        self.assertTrue(Student_Profile.objects.filter(User=user).exists())


class StudentProfileAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('erin', password='pass12345')

    def test_logged_in_user_can_reach_their_profile_page(self):
        client = Client()
        client.force_login(self.user)
        response = client.get('/students/profile/')
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_from_profile_page(self):
        client = Client()
        response = client.get('/students/profile/')
        self.assertEqual(response.status_code, 302)
