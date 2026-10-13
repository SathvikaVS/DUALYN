from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    path('upload/', views.upload_resume_view, name='upload'),
    path('<int:pk>/sync/', views.sync_resume_view, name='sync'),
    path('', views.resume_list_view, name='list'),
]