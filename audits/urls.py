from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('site/<str:site_name>/', views.site_detail, name='site_detail'),
    path('report/<int:report_id>/', views.report_detail, name='report_detail'),
]
