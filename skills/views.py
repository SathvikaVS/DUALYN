from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from analysis.services.gap_engine import recalculate_analysis
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

            # Keep active benchmark diagnostics in sync
            for a in request.user.analyses.all():
                recalculate_analysis(a)

            messages.success(request, f"Added '{skill_entry.skill.name}' to your declared competencies.")
            return redirect('skills:my_skills')
    else:
        form = StudentSkillForm()

    declared = request.user.declared_skills.select_related('skill')
    latest_resume = request.user.resumes.order_by('-uploaded_at').first()
    resume_skills = latest_resume.ai_extracted_skills.all() if latest_resume else []
    declared_skill_ids = set(declared.values_list('skill_id', flat=True))

    return render(request, 'skills/my_skills.html', {
        'form': form,
        'declared': declared,
        'latest_resume': latest_resume,
        'resume_skills': resume_skills,
        'declared_skill_ids': declared_skill_ids,
    })


@login_required
def sync_all_resume_skills_view(request):
    """
    Imports all AI-extracted competencies from the student's latest uploaded resume
    directly into their declared skills, and recalculates readiness benchmarks.
    """
    latest_resume = request.user.resumes.order_by('-uploaded_at').first()
    if not latest_resume or not latest_resume.ai_extracted_skills.exists():
        messages.warning(request, "No resume competencies found to sync. Please upload a resume first.")
        return redirect('skills:my_skills')

    synced_count = 0
    for s in latest_resume.ai_extracted_skills.all():
        _, created = StudentSkill.objects.get_or_create(
            student=request.user,
            skill=s,
            defaults={'level': 'intermediate'}
        )
        if created:
            synced_count += 1

    for a in request.user.analyses.all():
        recalculate_analysis(a)

    messages.success(
        request,
        f"Synchronized {latest_resume.ai_extracted_skills.count()} competencies from your resume into your profile. "
        f"Readiness diagnostics updated."
    )
    return redirect('skills:my_skills')


@login_required
def remove_skill_view(request, pk):
    entry = get_object_or_404(StudentSkill, pk=pk, student=request.user)
    skill_name = entry.skill.name
    entry.delete()

    for a in request.user.analyses.all():
        recalculate_analysis(a)

    messages.success(request, f"Removed '{skill_name}' from declared competencies.")
    return redirect('skills:my_skills')
