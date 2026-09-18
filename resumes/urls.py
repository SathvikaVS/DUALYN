from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    path('upload/', views.upload_resume_view, name='upload'),
    path('', views.resume_list_view, name='list'),
]