from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import RunAnalysisForm
from .models import SkillAnalysis
from .services.gap_engine import run_analysis
from recommendations.services.recommendation_engine import generate_recommendations
from .services.progress import compare_analyses


@login_required
def report_view(request, pk):
    analysis = get_object_or_404(SkillAnalysis, pk=pk, student=request.user)
    latest_resume = request.user.resumes.order_by('-uploaded_at').first()

    # If the analysis was created before the resume was uploaded, or is stale, recalculate it in-place
    if latest_resume and (analysis.created_at < latest_resume.uploaded_at or (analysis.readiness_score == 0 and latest_resume.extracted_text)):
        from .services.gap_engine import recalculate_analysis
        analysis = recalculate_analysis(analysis)

    # Ensure roadmap exists for this analysis
    if not hasattr(analysis, 'roadmap') or not analysis.roadmap:
        generate_recommendations(analysis)
        analysis.refresh_from_db()

    gaps = analysis.gaps.select_related('skill').order_by('status', '-priority')

    previous = request.user.analyses.filter(
        job_role=analysis.job_role, created_at__lt=analysis.created_at
    ).first()
    progress = compare_analyses(previous, analysis) if previous else None

    return render(request, 'analysis/report.html', {
        'analysis': analysis,
        'gaps': gaps,
        'previous': previous,
        'progress': progress,
    })


@login_required
def history_view(request):
    analyses = request.user.analyses.select_related('job_role')
    return render(request, 'analysis/history.html', {'analyses': analyses})


@login_required
def run_analysis_view(request):
    latest_resume = request.user.resumes.order_by('-uploaded_at').first()
    detected_role = None
    detected_headline = ""

    if latest_resume:
        detected_role = latest_resume.get_detected_role()
        detected_headline = latest_resume.get_headline()

    if request.method == 'POST':
        form = RunAnalysisForm(request.POST)
        if form.is_valid():
            selected_role = form.cleaned_data['job_role']
            analysis = run_analysis(request.user, selected_role)
            generate_recommendations(analysis)
            return redirect('analysis:report', pk=analysis.pk)
    else:
        initial = {}
        if detected_role:
            initial['job_role'] = detected_role
        form = RunAnalysisForm(initial=initial)

    return render(request, 'analysis/run.html', {
        'form': form,
        'detected_role': detected_role,
        'detected_headline': detected_headline,
        'latest_resume': latest_resume,
    })

@login_required
def compare_view(request):
    analyses = request.user.analyses.select_related('job_role')
    old_id = request.GET.get('old', '')
    new_id = request.GET.get('new', '')
    context = {'analyses': analyses}

    if old_id and new_id:
        if not (old_id.isdigit() and new_id.isdigit()):
            context['error'] = "Please choose two analyses from the lists."
        else:
            old = get_object_or_404(SkillAnalysis, pk=old_id, student=request.user)
            new = get_object_or_404(SkillAnalysis, pk=new_id, student=request.user)
            context.update({
                'old': old,
                'new': new,
                'result': compare_analyses(old, new),
                'different_roles': old.job_role_id != new.job_role_id,
            })

    return render(request, 'analysis/compare.html', context)