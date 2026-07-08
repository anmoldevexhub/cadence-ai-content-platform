from django.urls import path
from . import views

urlpatterns = [
    path('', views.WebsiteListCreateView.as_view()),
    path('<int:pk>/', views.WebsiteDetailView.as_view()),
    path('<int:pk>/crawl/', views.TriggerCrawlView.as_view()),
    path('<int:pk>/crawl-status/', views.CrawlStatusView.as_view()),
    path('<int:pk>/social/', views.SocialConnectionView.as_view()),
    path('<int:pk>/social/<int:conn_pk>/', views.SocialConnectionDetailView.as_view()),
    path('<int:pk>/social/<str:platform>/test/', views.TestConnectionView.as_view()),
    path('<int:pk>/stats/', views.WebsiteStatsView.as_view()),
    path('<int:pk>/pages/', views.WebsitePagesListView.as_view()),
    path('<int:pk>/samples/', views.SampleContentView.as_view()),
    path('<int:pk>/samples/<int:sample_pk>/', views.SampleContentDetailView.as_view()),
]