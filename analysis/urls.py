from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('best-fit/', views.best_fit_view, name='best_fit'),
    path('run/', views.run_analysis_view, name='run'),
    path('report/<int:pk>/', views.report_view, name='report'),
    path('report/<int:pk>/refresh/', views.refresh_analysis_view, name='refresh'),
    path('report/<int:pk>/simulate/', views.simulate_view, name='simulate'),
    path('report/<int:pk>/share/create/', views.create_share_link_view, name='create_share_link'),
    path('share/<int:pk>/revoke/', views.revoke_share_link_view, name='revoke_share_link'),
    path('share/<str:token>/revoke/', views.revoke_share_link_view, name='revoke_share_link_token'),
    path('share/<str:token>/', views.public_share_view, name='public_share'),
    path('history/', views.history_view, name='history'),
    path('compare/', views.compare_view, name='compare'),
]