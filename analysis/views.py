from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import RunAnalysisForm
from .models import SkillAnalysis
from .services.gap_engine import run_analysis
from recommendations.services.recommendation_engine import generate_recommendations
from .services.progress import compare_analyses


@login_required
def run_analysis_view(request):
    if request.method == 'POST':
        form = RunAnalysisForm(request.POST)
        if form.is_valid():
            analysis = run_analysis(request.user, form.cleaned_data['job_role'])
            return redirect('analysis:report', pk=analysis.pk)
    else:
        form = RunAnalysisForm()
    return render(request, 'analysis/run.html', {'form': form})


@login_required
def report_view(request, pk):
    analysis = get_object_or_404(SkillAnalysis, pk=pk, student=request.user)
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
    if request.method == 'POST':
        form = RunAnalysisForm(request.POST)
        if form.is_valid():
            analysis = run_analysis(request.user, form.cleaned_data['job_role'])
            generate_recommendations(analysis)
            return redirect('analysis:report', pk=analysis.pk)
    else:
        form = RunAnalysisForm()
    return render(request, 'analysis/run.html', {'form': form})

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