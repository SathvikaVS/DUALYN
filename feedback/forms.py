from django import forms

from .models import Feedback


class FeedbackForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=(
            (1, 'Poor'),
            (2, 'Fair'),
            (3, 'Good'),
            (4, 'Very good'),
            (5, 'Excellent'),
        ),
        coerce=int,
        widget=forms.RadioSelect,
        label='How would you rate your experience?',
    )

    class Meta:
        model = Feedback
        fields = ('title', 'message', 'rating')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. The role analysis was easy to understand',
                'maxlength': 120,
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Tell us what worked well or what we could improve…',
                'rows': 5,
                'maxlength': 2000,
            }),
        }
        labels = {
            'title': 'Give your feedback a short title',
            'message': 'What would you like us to know?',
        }
        help_texts = {
            'message': 'Please don’t include passwords or other sensitive information.',
        }
