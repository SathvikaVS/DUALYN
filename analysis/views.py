import datetime
import json
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .forms import RunAnalysisForm
from .models import SkillAnalysis, ShareLink
from .services.gap_engine import run_analysis
from recommendations.services.recommendation_engine import generate_recommendations
from .services.progress import compare_analyses
from .services.freshness import evidence_changed_since
from .services.best_fit import rank_roles_for
from .services.simulate import simulate_score
from .services.unproven import unproven_claims


@login_required
def report_view(request, pk):
    analysis = get_object_or_404(SkillAnalysis, pk=pk, student=request.user)

    # Ensure roadmap exists for this analysis
    if not hasattr(analysis, 'roadmap') or not analysis.roadmap:
        generate_recommendations(analysis)
        analysis.refresh_from_db()

    gaps = analysis.gaps.select_related('skill').order_by('status', '-priority')

    previous = request.user.analyses.filter(
        job_role=analysis.job_role, created_at__lt=analysis.created_at
    ).first()
    progress = compare_analyses(previous, analysis) if previous else None

    unproven = unproven_claims(analysis)
    active_share_links = analysis.share_links.filter(
        revoked_at__isnull=True,
        expires_at__gt=timezone.now()
    )

    return render(request, 'analysis/report.html', {
        'analysis': analysis,
        'gaps': gaps,
        'previous': previous,
        'progress': progress,
        'is_stale': evidence_changed_since(analysis),
        'unproven': unproven,
        'unproven_claims': unproven,
        'active_share_links': active_share_links,
    })


@login_required
@require_POST
def refresh_analysis_view(request, pk):
    analysis = get_object_or_404(SkillAnalysis, pk=pk, student=request.user)
    new = run_analysis(request.user, analysis.job_role)
    generate_recommendations(new)
    messages.success(request, f"New check created for '{analysis.job_role.title}' with your latest information.")
    return redirect('analysis:report', pk=new.pk)


@login_required
@require_POST
def simulate_view(request, pk):
    analysis = get_object_or_404(SkillAnalysis, pk=pk, student=request.user)

    skill_ids = []
    if request.body:
        try:
            payload = json.loads(request.body.decode('utf-8'))
            if isinstance(payload, dict):
                skill_ids = payload.get('skill_ids', [])
            elif isinstance(payload, list):
                skill_ids = payload
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    if not skill_ids and request.POST:
        skill_ids = request.POST.getlist('skill_ids') or request.POST.getlist('skill_ids[]')

    projected = simulate_score(analysis, skill_ids)
    current = round(float(analysis.readiness_score), 1)
    projected = round(float(projected), 1)
    gain = round(max(0.0, projected - current), 1)

    return JsonResponse({
        'current': current,
        'projected': projected,
        'gain': gain,
    })


@login_required
@require_POST
def create_share_link_view(request, pk):
    analysis = get_object_or_404(SkillAnalysis, pk=pk, student=request.user)

    days_str = request.POST.get('days', '7')
    try:
        days = int(days_str)
        if days not in (7, 14, 30):
            days = 7
    except (ValueError, TypeError):
        days = 7

    if 'hide_name_submitted' in request.POST:
        hide_name = ('hide_name' in request.POST)
    else:
        raw_hide_name = request.POST.get('hide_name')
        if raw_hide_name is None:
            hide_name = True
        elif isinstance(raw_hide_name, bool):
            hide_name = raw_hide_name
        else:
            hide_name = str(raw_hide_name).lower() not in ('false', '0', 'off')

    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + datetime.timedelta(days=days)
    ShareLink.objects.create(
        analysis=analysis,
        token=token,
        expires_at=expires_at,
        hide_name=hide_name,
    )
    messages.success(request, f"Private share link created (valid for {days} days).")
    return redirect('analysis:report', pk=analysis.pk)


@login_required
@require_POST
def revoke_share_link_view(request, pk=None, token=None):
    if pk is not None:
        link = get_object_or_404(ShareLink, pk=pk, analysis__student=request.user)
    elif token is not None:
        link = get_object_or_404(ShareLink, token=token, analysis__student=request.user)
    else:
        link_id = request.POST.get('pk') or request.POST.get('link_id')
        link_token = request.POST.get('token')
        if link_id:
            link = get_object_or_404(ShareLink, pk=link_id, analysis__student=request.user)
        elif link_token:
            link = get_object_or_404(ShareLink, token=link_token, analysis__student=request.user)
        else:
            raise Http404("Share link not found.")

    link.revoked_at = timezone.now()
    link.save(update_fields=['revoked_at'])
    messages.success(request, "Share link has been revoked.")
    return redirect('analysis:report', pk=link.analysis.pk)


def public_share_view(request, token):
    link = get_object_or_404(
        ShareLink.objects.select_related('analysis__job_role', 'analysis__student'),
        token=token
    )
    if link.revoked_at is not None or link.expires_at <= timezone.now():
        raise Http404("This share link has expired or been revoked.")

    analysis = link.analysis
    gaps = analysis.gaps.select_related('skill').order_by('status', '-priority')
    roadmap = getattr(analysis, 'roadmap', None)

    full_name = None
    if not link.hide_name:
        profile = getattr(analysis.student, 'student_profile', None)
        if profile and profile.Full_name and profile.Full_name.strip():
            full_name = profile.Full_name.strip()
        else:
            full_name = analysis.student.get_full_name() or ""

    context = {
        'link': link,
        'analysis': analysis,
        'job_role': analysis.job_role,
        'readiness_score': analysis.readiness_score,
        'gaps': gaps,
        'roadmap': roadmap,
        'full_name': full_name,
    }
    response = render(request, 'analysis/public_share.html', context)
    response['Cache-Control'] = 'no-store'
    return response


@login_required
def best_fit_view(request):
    ranked_roles = rank_roles_for(request.user)
    return render(request, 'analysis/best_fit.html', {
        'ranked_roles': ranked_roles,
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