from django.db import models
from accounts.models import CustomUser
from websites.models import Website

class ContentIdea(models.Model):
    """Admin submits ideas/topics for a batch of content."""
    PLATFORM_CHOICES = [
        ('blog', 'Blog'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('facebook', 'Facebook'),
        ('youtube', 'YouTube'),
    ]
    
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='content_ideas')
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=300)          # Main topic
    context = models.TextField(blank=True)            # Admin's idea / brief
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES, default='blog')
    meta_tags = models.JSONField(default=list)        # ["SEO", "beginner", ...]
    target_date = models.DateField(null=True, blank=True)
    target_time = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending','Pending'),('generating','Generating'),
                 ('done','Done'),('failed','Failed')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.platform}] {self.title}"


class ContentDraft(models.Model):
    """AI-generated draft, pending admin approval."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
    ]
    PLATFORM_CHOICES = ContentIdea.PLATFORM_CHOICES

    idea = models.ForeignKey(ContentIdea, on_delete=models.CASCADE,
                             related_name='drafts', null=True, blank=True)
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='drafts')
    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    title = models.CharField(max_length=300)
    body = models.TextField()                    # Full HTML/MD content for blogs
    excerpt = models.TextField(blank=True)       # Short preview
    meta_description = models.TextField(blank=True)
    tags = models.JSONField(default=list)
    word_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Review tracking
    reviewed_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_drafts'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # AI metadata
    ai_model = models.CharField(max_length=50, default='gpt-4o-mini')
    generation_prompt = models.TextField(blank=True)  # stored for debugging / regen
    cover_image = models.CharField(max_length=500, blank=True)
    category = models.CharField(max_length=100, blank=True)
    author_name = models.CharField(max_length=100, blank=True, default="")
    custom_date = models.CharField(max_length=50, blank=True, default="")
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status}] {self.title}"

    def save(self, *args, **kwargs):
        self.word_count = len(self.body.split())
        if not self.pk:
            if not self.author_name:
                self.author_name = self.website.name
            if not self.category:
                self.category = self.website.industry or "Marketing"
            if not self.custom_date:
                from django.utils import timezone
                self.custom_date = timezone.now().strftime("%B %d, %Y")
        super().save(*args, **kwargs)


class ScheduledPost(models.Model):
    """Links an approved draft to a publish date/time."""
    draft = models.OneToOneField(ContentDraft, on_delete=models.CASCADE,
                                  related_name='scheduled_post')
    scheduled_for = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    make_response = models.JSONField(null=True, blank=True)   # Store make.com response
    is_published = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['scheduled_for']

    def __str__(self):
        return f"{self.draft.title} @ {self.scheduled_for}"