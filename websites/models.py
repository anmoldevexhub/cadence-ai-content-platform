from django.db import models
from accounts.models import CustomUser

class Website(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('draft', 'Draft'),
    ]
    
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=200, unique=True)  # e.g. "northwindcoffee.com"
    url = models.URLField()                                   # e.g. "https://northwindcoffee.com"
    industry = models.CharField(max_length=100, blank=True)
    tone = models.CharField(max_length=200, blank=True)      # e.g. "Warm, artisanal"
    style_guide = models.JSONField(default=dict, blank=True)  # Detailed style guide extracted from crawl
    needs_crawl = models.BooleanField(default=True)  # Flag to indicate if website needs crawling
    topics = models.JSONField(default=list)                  # ["Specialty coffee", ...]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    color = models.CharField(max_length=7, default='#6366f1')  # for avatar
    brand_colors = models.JSONField(default=list)                  # ["#b45309", ...]
    avg_read_time = models.CharField(max_length=50, blank=True, default='4.0m')
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='websites')
    contact_email = models.CharField(max_length=200, blank=True, default='')
    contact_phone = models.CharField(max_length=50, blank=True, default='')
    logo_url = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Scrape metadata stored here after crawl
    scrape_summary = models.TextField(blank=True)            # AI-summarized style guide
    scrape_status = models.CharField(
        max_length=20,
        choices=[('pending','Pending'),('crawling','Crawling'),('done','Done'),('failed','Failed')],
        default='pending'
    )
    last_crawled = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def short(self):
        return self.name[0].upper()


class SocialConnection(models.Model):
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
        ('youtube', 'YouTube'),
        ('twitter', 'Twitter/X'),
        ('blog', 'Blog (Website)'),
    ]
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='social_connections')
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    make_webhook_url = models.URLField(blank=True)   # platform-specific make.com hook
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['website', 'platform']

    def __str__(self):
        return f"{self.website.name} → {self.platform}"


class ScrapeResult(models.Model):
    """Stores individual crawled pages for context."""
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='scraped_pages')
    page_url = models.URLField()
    page_title = models.CharField(max_length=500, blank=True)
    raw_text = models.TextField()
    heading_structure = models.JSONField(default=list)   # [{"level": "h2", "text": "..."}]
    
    # New structured extraction fields
    meta_title = models.CharField(max_length=500, blank=True)
    meta_description = models.TextField(blank=True)
    og_properties = models.JSONField(default=dict, blank=True)
    publication_date = models.DateTimeField(null=True, blank=True)
    author = models.CharField(max_length=200, blank=True)
    categories_tags = models.JSONField(default=list, blank=True)
    image_alts = models.JSONField(default=list, blank=True)
    page_type = models.CharField(max_length=50, blank=True)
    
    # Metrics and NLP analysis
    readability_metrics = models.JSONField(default=dict, blank=True)
    sentiment_metrics = models.JSONField(default=dict, blank=True)
    entities = models.JSONField(default=list, blank=True)
    key_phrases = models.JSONField(default=list, blank=True)
    
    # Extracted interactive elements
    comments = models.JSONField(default=list, blank=True)
    ctas = models.JSONField(default=list, blank=True)
    
    # Readability-extracted clean HTML content
    main_content = models.TextField(blank=True)
    
    crawled_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-crawled_at']