from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Feedback


class FeedbackSubmissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='feedback-user',
            password='test-password-123',
        )
        self.url = reverse('feedback:submit')

    def test_anonymous_user_is_redirected_to_sign_in(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_feedback_page_renders_for_signed_in_user(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'feedback/submit.html')
        self.assertContains(response, 'css/feedback.css')
        self.assertContains(response, 'rating-5')

    def test_valid_feedback_is_saved_to_the_signed_in_user(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url, {
            'title': 'Clear role report',
            'message': 'The suggested next steps were useful.',
            'rating': '5',
        })

        self.assertRedirects(response, self.url)
        feedback = Feedback.objects.get()
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.rating, 5)

    def test_login_page_preserves_feedback_redirect_and_has_no_merge_markers(self):
        response = self.client.get(reverse('accounts:login'), {'next': self.url})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'name="next" value="{self.url}"')
        self.assertNotContains(response, '<<<<<<<')

    def test_rating_outside_range_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url, {
            'title': 'Invalid rating',
            'message': 'This should not be saved.',
            'rating': '6',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Feedback.objects.exists())
        self.assertTrue(response.context['form'].errors)
