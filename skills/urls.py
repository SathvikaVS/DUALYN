from django.urls import path
from . import views

app_name = 'skills'

urlpatterns = [
    path('my-skills/', views.my_skills_view, name='my_skills'),
    path('my-skills/<int:pk>/remove/', views.remove_skill_view, name='remove_skill'),
]