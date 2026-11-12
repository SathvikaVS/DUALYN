from django.shortcuts import render
from recommendations.models import RoadmapItem
from analysis.services.freshness import evidence_changed_since


def dashboard_view(request):
    """
    Root URL. Anonymous visitors see the public landing page (Section 4's
    flow puts "Landing Page" before Register/Login). Logged-in students
    see their dashboard. Kept as one view, under the existing url name
    'dashboard', so every template's {% url 'dashboard' %} link keeps
    working for both cases.
    """
    if not request.user.is_authenticated:
        return render(request, 'landing.html')

    user = request.user
    profile = getattr(user, 'student_profile', None)
    display_name = profile.Full_name if profile else user.username
    latest_resume = user.resumes.order_by('-uploaded_at').first()
    analyses = user.analyses.select_related('job_role')
    latest = analyses.first()

    context = {
        'display_name': display_name,
        'latest': latest,
        'recent': analyses[:5],
        'latest_resume': latest_resume,
        'resume_skills_count': latest_resume.ai_extracted_skills.count() if latest_resume else 0,
        'latest_is_stale': bool(latest) and evidence_changed_since(latest),
    }
    if latest:
        gaps = latest.gaps.select_related('skill')
        matched_skills = gaps.filter(
            status__in=['covered', 'demonstrated']
        ).order_by('skill__name')
        matched_count = matched_skills.count()
        context.update({
            'matched_count': matched_count,
            'matched_skills': matched_skills[:5],
            'covered_count': matched_count,
            'improve_count': gaps.filter(status__in=['needs_improvement', 'mentioned']).count(),
            'missing_count': gaps.filter(status__in=['missing', 'not_assessed']).count(),
            'high_priority': gaps.filter(priority='high').exclude(status__in=['covered', 'demonstrated']),
            'next_skills': RoadmapItem.objects.filter(
                roadmap__analysis=latest, phase__in=[1, 2]
            ).select_related('skill_gap__skill')[:3],
        })
    return render(request, 'dashboard.html', context)