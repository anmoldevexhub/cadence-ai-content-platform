from celery import shared_task
import logging
from django.utils import timezone

from .models import Website, ScrapeResult
from .scraper import scrape_website
from logs.models import ActivityLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def crawl_website_task(self, website_id: int):
    try:
        website = Website.objects.get(pk=website_id)
        website.scrape_status = 'crawling'
        website.save(update_fields=['scrape_status'])
        
        result = scrape_website(website.url)
        
        # Store individual pages
        ScrapeResult.objects.filter(website=website).delete()  # fresh crawl
        from .crawler import calculate_readability_metrics, analyze_sentiment, extract_entities, extract_key_phrases
        
        for page in result['pages']:
            # Calculate metrics per page
            readability = calculate_readability_metrics(page['text'])
            sentiment = analyze_sentiment(page['text'])
            entities = extract_entities(page['text'])
            key_phrases = extract_key_phrases(page['text'])
            
            ScrapeResult.objects.create(
                website=website,
                page_url=page['url'],
                page_title=page['title'],
                raw_text=page['text'],
                heading_structure=page['headings'],
                
                # New fields
                meta_title=page.get('meta_title', ''),
                meta_description=page.get('meta_description', ''),
                og_properties=page.get('og_properties', {}),
                publication_date=page.get('publication_date'),
                author=page.get('author', ''),
                categories_tags=page.get('categories_tags', []),
                image_alts=page.get('image_alts', []),
                page_type=page.get('page_type', 'other'),
                
                # Metrics
                readability_metrics=readability,
                sentiment_metrics=sentiment,
                entities=entities,
                key_phrases=key_phrases,
                
                # Interactive elements
                comments=page.get('comments', []),
                ctas=page.get('ctas', []),
                main_content=page.get('main_content', ''),
            )
        
        # Use AI to summarize the style/tone and extract metadata
        from content.generator import summarize_website_style, analyze_website_context
        from .crawler import build_advanced_style_guide
        
        try:
            style_summary = summarize_website_style(result['structure_summary'])
        except Exception as e:
            logger.error(f"Task style summary generation error: {e}")
            style_summary = (
                "Write in a professional, clear, and engaging tone. Structure the content logically with an introduction, "
                "subheadings, and clear call-to-actions. Keep the paragraphs concise and use bullet points for readability. "
                "Target key audience interests and write in a brand-consistent voice."
            )
        
        try:
            analysis = analyze_website_context(result['structure_summary'])
            website.industry = analysis.get('industry', website.industry or 'General')
            website.tone = analysis.get('tone', website.tone or 'Professional')
            website.topics = analysis.get('topics', website.topics)
            
            # Prioritize real CSS colors from homepage, fall back to LLM suggestions
            homepage_colors = result['pages'][0].get('brand_colors', []) if result.get('pages') else []
            if homepage_colors:
                website.brand_colors = homepage_colors
            else:
                website.brand_colors = analysis.get('brand_colors', website.brand_colors)
                
            website.avg_read_time = analysis.get('avg_read_time', website.avg_read_time)
        except Exception as e:
            logger.error(f"Task context analysis error: {e}")
            
        try:
            homepage_styles = result['pages'][0] if result.get('pages') else None
            style_guide_data = build_advanced_style_guide(website.id, homepage_styles)
            website.style_guide = style_guide_data
        except Exception as e:
            logger.error(f"Task style guide extraction error: {e}")
            style_guide_data = {}

        website.scrape_summary = style_summary
        website.scrape_status = 'done'
        website.needs_crawl = False
        website.last_crawled = timezone.now()
        
        # Extract contact information
        scraped_emails = []
        scraped_phones = []
        scraped_logo = ""
        
        for p in result['pages']:
            if p.get('scraped_emails'):
                scraped_emails.extend(p['scraped_emails'])
            if p.get('scraped_phones'):
                scraped_phones.extend(p['scraped_phones'])
            if not scraped_logo and p.get('logo_url'):
                scraped_logo = p['logo_url']
                
        scraped_emails = list(dict.fromkeys(scraped_emails))
        scraped_phones = list(dict.fromkeys(scraped_phones))
        
        if scraped_emails and not website.contact_email:
            website.contact_email = scraped_emails[0]
        if scraped_phones and not website.contact_phone:
            website.contact_phone = scraped_phones[0]
            
        if scraped_logo and not website.logo_url:
            try:
                from .crawler import download_and_save_logo
                website.logo_url = download_and_save_logo(website, scraped_logo)
            except Exception as e:
                logger.error(f"Failed to download and save logo: {e}")
            
        website.save(update_fields=[
            'scrape_summary', 'scrape_status', 'last_crawled', 
            'industry', 'tone', 'topics', 'brand_colors', 'avg_read_time',
            'style_guide', 'needs_crawl', 'contact_email', 'contact_phone', 'logo_url'
        ])
        
        ActivityLog.objects.create(
            actor=None, actor_name='System',
            action='crawl_done', target_description=website.name
        )
        logger.info(f"Crawl completed for {website.name}")
        return {'status': 'done', 'pages': len(result['pages'])}
    
    except Exception as exc:
        logger.error(f"Crawl failed for website {website_id}: {exc}")
        Website.objects.filter(pk=website_id).update(scrape_status='failed')
        from django.conf import settings
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) or self.request.called_directly:
            return {'status': 'failed', 'error': str(exc)}
        raise self.retry(exc=exc, countdown=60)