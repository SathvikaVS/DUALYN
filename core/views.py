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
    analyses = user.analyses.select_related('job_role')
    latest = analyses.first()
    context = {'display_name': display_name, 'latest': latest, 'recent': analyses[:5]}
    if latest:
        gaps = latest.gaps.select_related('skill')
        context.update({
            'covered_count': gaps.filter(status='covered').count(),
            'improve_count': gaps.filter(status='needs_improvement').count(),
            'missing_count': gaps.filter(status='missing').count(),
            'high_priority': gaps.filter(priority='high').exclude(status='covered'),
            'next_skills': RoadmapItem.objects.filter(
                roadmap__analysis=latest, phase__in=[1, 2]
            ).select_related('skill_gap__skill')[:3],
        })
    return render(request, 'dashboard.html', context)