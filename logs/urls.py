from django.urls import path
from . import views

urlpatterns = [
    path('logins/', views.LoginLogListView.as_view()),
    path('activity/', views.ActivityLogListView.as_view()),
    path('dashboard/', views.DashboardAnalyticsView.as_view()),
]