from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import StudentSkillForm
from .models import StudentSkill


@login_required
def my_skills_view(request):
    if request.method == 'POST':
        form = StudentSkillForm(request.POST)
        if form.is_valid():
            skill_entry = form.save(commit=False)
            skill_entry.student = request.user
            skill_entry.save()
            messages.success(request, "Skill added.")
            return redirect('skills:my_skills')
    else:
        form = StudentSkillForm()

    declared = request.user.declared_skills.select_related('skill')
    return render(request, 'skills/my_skills.html', {'form': form, 'declared': declared})


@login_required
def remove_skill_view(request, pk):
    entry = get_object_or_404(StudentSkill, pk=pk, student=request.user)
    entry.delete()
    messages.success(request, "Skill removed.")
    return redirect('skills:my_skills')
