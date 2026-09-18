from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ResumeUploadForm
from .services.resume_parser import extract_text_from_resume


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
                messages.success(request, "Resume uploaded and processed successfully.")
            else:
                messages.warning(request, "Resume uploaded, but text extraction failed. You may need to re-upload a clearer file.")

            return redirect('resumes:list')
        else:
            messages.error(request, "Please upload a valid PDF or DOCX file.")
    else:
        form = ResumeUploadForm()
    return render(request, 'resumes/upload.html', {'form': form})


@login_required
def resume_list_view(request):
    resumes = request.user.resumes.all()
    return render(request, 'resumes/list.html', {'resumes': resumes})
