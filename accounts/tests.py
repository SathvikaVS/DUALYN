from django.test import TestCase
from django.contrib.auth.models import User

from .models import UserRole


class RegisterViewTests(TestCase):
    def test_registration_creates_a_student_role_profile(self):
        response = self.client.post(
            '/accounts/register/',
            {
                'username': 'new-student',
                'email': 'student@example.com',
                'password1': 'SafePassword#842',
                'password2': 'SafePassword#842',
            },
        )

        self.assertRedirects(response, '/')
        user = User.objects.get(username='new-student')
        self.assertEqual(user.role_profile.role, UserRole.STUDENT)
        self.assertEqual(
            int(response.wsgi_request.session['_auth_user_id']),
            user.pk,
        )

    def test_invalid_registration_displays_field_errors(self):
        response = self.client.post(
            '/accounts/register/',
            {
                'username': 'new-student',
                'email': 'not-an-email',
                'password1': 'short',
                'password2': 'short',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid email address.')
        self.assertContains(response, 'This password is too short.')
        self.assertFalse(User.objects.filter(username='new-student').exists())

    def test_registration_page_renders_auth_styles(self):
        response = self.client.get('/accounts/register/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'auth-input-group')


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='existing-user',
            password='SafePassword#842',
        )

    def test_login_page_renders_auth_styles(self):
        response = self.client.get('/accounts/login/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'auth-input-group')

    def test_invalid_login_displays_authentication_error(self):
        response = self.client.post(
            '/accounts/login/',
            {'username': self.user.username, 'password': 'incorrect'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username and password.')

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(
            '/accounts/login/',
            {'username': self.user.username, 'password': 'SafePassword#842'},
        )

        self.assertRedirects(response, '/')
