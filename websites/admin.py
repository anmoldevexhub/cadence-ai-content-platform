from django.contrib import admin
from .models import Website, SocialConnection, ScrapeResult, SampleContent

admin.site.register(Website)
admin.site.register(SocialConnection)
admin.site.register(ScrapeResult)

@admin.register(SampleContent)
class SampleContentAdmin(admin.ModelAdmin):
    list_display = ['website', 'platform', 'title', 'file_name', 'is_active', 'uploaded_at']
    list_filter = ['platform', 'is_active', 'website']
    search_fields = ['title', 'content', 'file_name']

