from django.urls import path
from . import views

urlpatterns = [
    # Ideas (admin submits topics)
    path('ideas/', views.ContentIdeaListCreateView.as_view()),
    path('ideas/<int:pk>/', views.ContentIdeaDetailView.as_view()),
    path('ideas/<int:pk>/generate/', views.GenerateContentView.as_view()),

    # AI-powered idea suggestions (dynamic, per website)
    path('suggestions/', views.IdeaSuggestionsView.as_view()),

    # Drafts
    path('drafts/', views.ContentDraftListView.as_view()),
    path('drafts/<int:pk>/', views.ContentDraftDetailView.as_view()),
    path('drafts/<int:pk>/approve/', views.ApproveDraftView.as_view()),
    path('drafts/<int:pk>/reject/', views.RejectDraftView.as_view()),
    path('drafts/<int:pk>/regenerate/', views.RegenerateDraftView.as_view()),
    path('drafts/<int:pk>/schedule/', views.ScheduleDraftView.as_view()),
    path('drafts/<int:pk>/unschedule/', views.UnscheduleDraftView.as_view()),
    path('drafts/<int:pk>/republish/', views.RepublishDraftView.as_view()),
    path('drafts/<int:pk>/internal-links/', views.InjectInternalLinksView.as_view()),
    path('drafts/<int:pk>/remove-links/', views.RemoveInternalLinksView.as_view()),

    # Schedule
    path('scheduled/', views.ScheduledPostListView.as_view()),

    # Approvals queue (cross-website pending drafts)
    path('approvals/', views.ApprovalsQueueView.as_view()),
    
    # Token & API usage stats
    path('usage/stats/<int:pk>/', views.TokenUsageStatsView.as_view()),
]