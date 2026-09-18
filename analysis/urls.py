from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('run/', views.run_analysis_view, name='run'),
    path('report/<int:pk>/', views.report_view, name='report'),
    path('history/', views.history_view, name='history'),
]