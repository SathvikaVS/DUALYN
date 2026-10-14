import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from skills.models import StudentSkill
from jobs.services.role_profiles import sync_role_profiles_to_db
from analysis.services.gap_engine import recalculate_analysis
from .forms import ResumeUploadForm
from .models import Resume
from .services.resume_parser import extract_text_from_resume
from .services.skill_analyzer import extract_resume_skills, extract_resume_skills_with_evidence


def _sync_profile_from_resume(user, resume_text):
    """
    Non-destructively populates student profile metadata (Full name, College, Education level)
    from extracted resume text if currently unset or at default values.
    """
    profile = getattr(user, 'student_profile', None)
    if not profile or not resume_text:
        return

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if not lines:
        return

    updated = False
    # If full name is just username or blank, infer candidate's name from resume header
    if (not profile.Full_name or profile.Full_name == user.username) and len(lines) > 0:
        first_line = lines[0]
        if 2 <= len(first_line) <= 50 and not re.search(r'(?i)\b(?:resume|cv|curriculum|vitae|page|contact)\b', first_line):
            words = first_line.split()
            if 1 <= len(words) <= 5 and all(w.replace('.', '').replace('-', '').isalpha() for w in words):
                profile.Full_name = first_line.title() if first_line.isupper() else first_line
                updated = True

    # If college is empty, extract university/institution name
    if not profile.College:
        college_match = re.search(
            r'(?i)\b([A-Z][A-Za-z\s.,&-]+(?:College|University|Institute of Technology|Polytechnic|Academy))\b',
            resume_text
        )
        if college_match:
            coll_name = college_match.group(1).strip()
            if len(coll_name) <= 100:
                profile.College = coll_name
                updated = True

    # If education level is default, refine based on degree cues
    if profile.Education == 'Undergad':
        if re.search(r'(?i)\b(?:ph\.?d\.?|doctorate|research\s+scholar)\b', resume_text):
            profile.Education = 'PhD'
            updated = True
        elif re.search(r'(?i)\b(?:mca|m\.tech|m\.s\.|msc|master(?:\'?s)?|postgrad(?:uate)?)\b', resume_text):
            profile.Education = 'Postgrad'
            updated = True

    if updated:
        try:
            profile.save()
        except Exception:
            pass


@login_required
def upload_resume_view(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.student = request.user
            resume.save()

            # Ensure all canonical skills exist in catalog database
            sync_role_profiles_to_db()

            extracted = extract_text_from_resume(resume.file.path)
            if extracted:
                resume.extracted_text = extracted
                matched_skills, skills_evidence = extract_resume_skills_with_evidence(extracted)
                if matched_skills:
                    resume.ai_extracted_skills.set(matched_skills)
                    resume.skills_evidence = skills_evidence
                    resume.save()

                    # 1. Synchronize detected competencies into declared skills (student profile)
                    synced_count = 0
                    for skill in matched_skills:
                        _, created = StudentSkill.objects.get_or_create(
                            student=request.user,
                            skill=skill,
                            defaults={'level': 'intermediate'}
                        )
                        if created:
                            synced_count += 1

                    # Clean up any stale overlapping compound entries
                    matched_names = {s.name for s in matched_skills}
                    if 'HTML' in matched_names and 'CSS' in matched_names:
                        StudentSkill.objects.filter(student=request.user, skill__name='HTML & CSS').delete()
                    if 'Debugging' in matched_names and 'Testing' not in matched_names:
                        StudentSkill.objects.filter(student=request.user, skill__name='Testing & Debugging').delete()

                    # 2. Sync profile details (Full name, College, Education) if unset
                    _sync_profile_from_resume(request.user, extracted)

                    # 3. Recalculate any existing analyses to immediately update UI/UX benchmarks
                    user_analyses = list(request.user.analyses.all())
                    for a in user_analyses:
                        recalculate_analysis(a)

                    skill_names_str = ', '.join(s.name for s in matched_skills)
                    messages.success(
                        request,
                        f"Resume processed successfully! Detected {len(matched_skills)} competencies: "
                        f"{skill_names_str}. "
                        f"Your profile and career readiness benchmarks have been automatically updated."
                    )
                else:
                    resume.save()
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
    sync_role_profiles_to_db()
    resume = get_object_or_404(Resume, pk=pk, student=request.user)
    if resume.extracted_text:
        matched_skills, skills_evidence = extract_resume_skills_with_evidence(resume.extracted_text)
        if matched_skills:
            resume.ai_extracted_skills.set(matched_skills)
            resume.skills_evidence = skills_evidence
            resume.save()
        _sync_profile_from_resume(request.user, resume.extracted_text)

    skills = resume.ai_extracted_skills.all()
    for s in skills:
        StudentSkill.objects.get_or_create(
            student=request.user,
            skill=s,
            defaults={'level': 'intermediate'}
        )

    matched_names = {s.name for s in skills}
    if 'HTML' in matched_names and 'CSS' in matched_names:
        StudentSkill.objects.filter(student=request.user, skill__name='HTML & CSS').delete()
    if 'Debugging' in matched_names and 'Testing' not in matched_names:
        StudentSkill.objects.filter(student=request.user, skill__name='Testing & Debugging').delete()

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
