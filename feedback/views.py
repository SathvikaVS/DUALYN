from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import FeedbackForm


@login_required
def submit_feedback_view(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.save()
            messages.success(request, 'Thank you — your feedback has been sent.')
            return redirect('feedback:submit')
    else:
        form = FeedbackForm()

    return render(request, 'feedback/submit.html', {'form': form})
