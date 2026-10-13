from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from skills.models import StudentSkill
from analysis.services.gap_engine import recalculate_analysis
from .forms import ResumeUploadForm
from .models import Resume
from .services.resume_parser import extract_text_from_resume
from .services.skill_analyzer import extract_resume_skills


@login_required
def upload_resume_view(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.student = request.user
            resume.save()

            extracted = extract_text_from_resume(resume.file.path)
            if extracted:
                resume.extracted_text = extracted
                resume.save()

                matched_skills = extract_resume_skills(extracted)
                if matched_skills:
                    resume.ai_extracted_skills.set(matched_skills)

                    # 1. Synchronize detected competencies into declared skills
                    synced_count = 0
                    for skill in matched_skills:
                        _, created = StudentSkill.objects.get_or_create(
                            student=request.user,
                            skill=skill,
                            defaults={'level': 'intermediate'}
                        )
                        if created:
                            synced_count += 1

                    # 2. Recalculate any existing analyses to immediately update UI/UX benchmarks
                    user_analyses = list(request.user.analyses.all())
                    for a in user_analyses:
                        recalculate_analysis(a)

                    messages.success(
                        request,
                        f"Resume processed successfully! Detected {len(matched_skills)} competencies: "
                        f"{', '.join(s.name for s in matched_skills)}. "
                        f"Your profile and career readiness benchmarks have been automatically updated."
                    )
                else:
                    messages.success(request, "Resume uploaded and processed successfully.")
            else:
                messages.warning(request, "Resume uploaded, but text extraction failed. You may need to re-upload a clearer file.")
            return redirect('resumes:list')
    else:
        form = ResumeUploadForm()
    return render(request, 'resumes/upload.html', {'form': form})


@login_required
def sync_resume_view(request, pk):
    """
    Explicitly synchronizes a resume's verified competencies to the student's profile
    and recalculates all active career readiness benchmarks.
    """
    resume = get_object_or_404(Resume, pk=pk, student=request.user)
    if resume.extracted_text:
        matched_skills = extract_resume_skills(resume.extracted_text)
        if matched_skills:
            resume.ai_extracted_skills.set(matched_skills)

    skills = resume.ai_extracted_skills.all()
    for s in skills:
        StudentSkill.objects.get_or_create(
            student=request.user,
            skill=s,
            defaults={'level': 'intermediate'}
        )

    for a in request.user.analyses.all():
        recalculate_analysis(a)

    messages.success(
        request,
        f"Synchronized {skills.count()} competencies from '{resume.file.name.split('/')[-1]}' "
        f"into your profile. Active benchmark diagnostics refreshed."
    )
    return redirect('resumes:list')


@login_required
def resume_list_view(request):
    resumes = request.user.resumes.all()
    return render(request, 'resumes/list.html', {'resumes': resumes})

