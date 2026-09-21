from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import StudentProfileForm


@login_required
def profile_view(request):
    profile = request.user.student_profile
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('students:profile')
    else:
        form = StudentProfileForm(instance=profile)
    return render(request, 'students/profile.html', {'form': form})
