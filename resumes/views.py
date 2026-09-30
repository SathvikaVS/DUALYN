from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ResumeUploadForm
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
                    messages.success(
                        request,
                        f"Resume processed. Detected: {', '.join(s.name for s in matched_skills)}."
                    )
                else:
                    messages.success(request, "Resume uploaded and processed successfully.")
            else:
                messages.warning(request, "Resume uploaded, but text extraction failed. You may need to re-upload a clearer file.")

@login_required
def resume_list_view(request):
    resumes = request.user.resumes.all()
    return render(request, 'resumes/list.html', {'resumes': resumes})
