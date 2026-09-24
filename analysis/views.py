from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import RunAnalysisForm
from .models import SkillAnalysis
from .services.gap_engine import run_analysis
from recommendations.services.recommendation_engine import generate_recommendations


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
    return render(request, 'analysis/report.html', {'analysis': analysis, 'gaps': gaps})


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