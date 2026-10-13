from django.urls import path
from . import views

app_name = 'skills'

urlpatterns = [
    path('my-skills/', views.my_skills_view, name='my_skills'),
    path('my-skills/sync-resume/', views.sync_all_resume_skills_view, name='sync_resume'),
    path('my-skills/<int:pk>/remove/', views.remove_skill_view, name='remove_skill'),
]