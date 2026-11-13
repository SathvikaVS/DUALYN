from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('best-fit/', views.best_fit_view, name='best_fit'),
    path('run/', views.run_analysis_view, name='run'),
    path('report/<int:pk>/', views.report_view, name='report'),
    path('report/<int:pk>/refresh/', views.refresh_analysis_view, name='refresh'),
    path('history/', views.history_view, name='history'),
    path('compare/', views.compare_view, name='compare'),
]