from django.shortcuts import render
from recommendations.models import RoadmapItem


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

    # If the latest analysis was generated before a resume upload or is stale, recalculate it in-place
    if latest and latest_resume and (latest.created_at < latest_resume.uploaded_at or (latest.readiness_score == 0 and latest_resume.extracted_text)):
        from analysis.services.gap_engine import recalculate_analysis
        latest = recalculate_analysis(latest)

    context = {
        'display_name': display_name,
        'latest': latest,
        'recent': analyses[:5],
        'latest_resume': latest_resume,
        'resume_skills_count': latest_resume.ai_extracted_skills.count() if latest_resume else 0,
    }
    if latest:
        gaps = latest.gaps.select_related('skill')
        context.update({
            'covered_count': gaps.filter(status__in=['covered', 'demonstrated']).count(),
            'improve_count': gaps.filter(status__in=['needs_improvement', 'mentioned']).count(),
            'missing_count': gaps.filter(status__in=['missing', 'not_assessed']).count(),
            'high_priority': gaps.filter(priority='high').exclude(status__in=['covered', 'demonstrated']),
            'next_skills': RoadmapItem.objects.filter(
                roadmap__analysis=latest, phase__in=[1, 2]
            ).select_related('skill_gap__skill')[:3],
        })
    return render(request, 'dashboard.html', context)