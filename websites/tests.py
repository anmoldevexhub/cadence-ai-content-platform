from django.test import TestCase
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup
from django.utils import timezone
import datetime

from websites.models import Website, ScrapeResult, SocialConnection
from websites.scraper import (
    get_url_priority,
    parse_pub_date,
    _clean_html_structure,
    _score_content_nodes,
    _classify_page_type_helper,
    _extract_from_soup
)
from websites.crawler import (
    count_syllables,
    calculate_readability_metrics,
    analyze_sentiment,
    extract_entities,
    extract_key_phrases,
    build_advanced_style_guide
)

User = get_user_model()


class CrawlerScraperTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testowner@cadence.io",
            username="testowner",
            password="testpassword",
            role="admin"
        )
        self.website = Website.objects.create(
            name="Test Coffee",
            domain="testcoffee.com",
            url="https://testcoffee.com",
            owner=self.user,
            status="active"
        )

    def test_syllable_count(self):
        """Test syllable counting heuristics."""
        self.assertEqual(count_syllables("hello"), 2)
        self.assertEqual(count_syllables("beautiful"), 3)
        self.assertEqual(count_syllables("a"), 1)
        self.assertEqual(count_syllables("programming"), 3)
        self.assertEqual(count_syllables("the"), 1)

    def test_readability_metrics(self):
        """Test Flesch-Kincaid and Gunning-Fog readability scores."""
        simple_text = (
            "This is a simple sentence. Learning to write is very fun. "
            "Python is a great programming language to build web sites."
        )
        metrics = calculate_readability_metrics(simple_text)
        self.assertIn('flesch_reading_ease', metrics)
        self.assertIn('flesch_kincaid_grade', metrics)
        self.assertIn('gunning_fog', metrics)
        self.assertGreater(metrics['flesch_reading_ease'], 0.0)

    def test_sentiment_metrics(self):
        """Test sentiment polarity calculations."""
        pos_text = "This is a great, beautiful, perfect, and successful solution."
        neg_text = "This is a terrible, bad, slow, and failed implementation."
        
        pos_sentiment = analyze_sentiment(pos_text)
        neg_sentiment = analyze_sentiment(neg_text)
        
        self.assertGreater(pos_sentiment['polarity'], 0.0)
        self.assertLess(neg_sentiment['polarity'], 0.0)

    def test_entity_extraction(self):
        """Test named entity extraction heuristic."""
        text = "Google announced that Python is great. Marcus and Aisha agreed in London."
        entities = extract_entities(text)
        # Verify capitalized proper nouns are captured
        self.assertIn("Google", entities)
        self.assertIn("London", entities)

    def test_key_phrase_extraction(self):
        """Test extraction of key multi-word phrases."""
        text = (
            "Specialty coffee is the best brewing choice. Specialty coffee requires "
            "great care. Brewing choice matters."
        )
        phrases = extract_key_phrases(text)
        self.assertTrue(len(phrases) > 0)
        self.assertIn("specialty coffee", phrases)

    def test_get_url_priority(self):
        """Test heuristic priority mapping for crawling."""
        self.assertEqual(get_url_priority("https://testcoffee.com/blog/how-to-brew"), 1)
        self.assertEqual(get_url_priority("https://testcoffee.com/posts/my-post"), 1)
        self.assertEqual(get_url_priority("https://testcoffee.com/about-us"), 2)
        self.assertEqual(get_url_priority("https://testcoffee.com/blog?page=2"), 3)

    def test_parse_pub_date(self):
        """Test parsing of ISO and non-standard dates."""
        iso_str = "2026-06-15T10:00:00Z"
        parsed = parse_pub_date(iso_str)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.year, 2026)

    def test_html_cleaner_and_scoring(self):
        """Test main content identification and cleaning."""
        html = """
        <html>
            <body>
                <header>Navigation bar</header>
                <div class="sidebar">Ads and side links</div>
                <main id="main-content">
                    <article>
                        <h1>How to Brew Coffee</h1>
                        <p>This is the first paragraph explaining pour over methods.</p>
                        <p>This is the second paragraph which adds detail.</p>
                    </article>
                </main>
                <footer>Footer links</footer>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        main_node = soup.find('main')
        
        # Verify node scoring selects main/article
        scored = _score_content_nodes(soup)
        self.assertIn(scored.name, ['main', 'article'])
        
        # Verify cleaner strips header/footer but keeps paragraphs
        clean_html = _clean_html_structure(scored)
        self.assertIn("<p>", clean_html)
        self.assertNotIn("<header>", clean_html)
        self.assertNotIn("<footer>", clean_html)

    def test_page_type_classification(self):
        """Test page type classification heuristics."""
        soup = BeautifulSoup("<html><title>About Us</title></html>", 'html.parser')
        p_type = _classify_page_type_helper("https://testcoffee.com/about", soup, "", None)
        self.assertEqual(p_type, 'about page')
        
        soup_prod = BeautifulSoup("<html><body><button class='add-to-cart'>Add</button></body></html>", 'html.parser')
        p_type_prod = _classify_page_type_helper("https://testcoffee.com/p/specialty-bean", soup_prod, "", None)
        self.assertEqual(p_type_prod, 'product page')

    def test_extract_from_soup(self):
        """Test full page property extraction from BeautifulSoup."""
        html = """
        <html>
            <head>
                <title>Blog Title</title>
                <meta name="description" content="A nice meta description."/>
                <meta property="og:title" content="OG Blog Title"/>
                <meta property="og:image" content="https://testcoffee.com/cover.jpg"/>
                <meta property="article:published_time" content="2026-06-15T12:00:00Z"/>
                <meta name="author" content="Marcus Lee"/>
            </head>
            <body>
                <main id="content">
                    <h1>Blog Post Heading</h1>
                    <p>Pour-over coffee is great. It yields clean flavors. Specialty coffee is popular.</p>
                    <img src="/bean.jpg" alt="Specialty Coffee Bean"/>
                    <a href="/shop" class="btn cta">Get Started Now</a>
                </main>
                <div class="comments-section">
                    <div class="comment">
                        <p>This is a comment left by a user.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        page_data = _extract_from_soup(soup, "https://testcoffee.com/blog/1", html)
        
        self.assertEqual(page_data['author'], "Marcus Lee")
        self.assertEqual(page_data['meta_description'], "A nice meta description.")
        self.assertIn("Specialty Coffee Bean", page_data['image_alts'])
        self.assertIn("Get Started Now", page_data['ctas'])
        self.assertIn("This is a comment left by a user.", page_data['comments'])

    def test_build_advanced_style_guide(self):
        """Test aggregation of style metrics across scraped page results."""
        # Create test scraped pages
        ScrapeResult.objects.create(
            website=self.website,
            page_url="https://testcoffee.com/blog/1",
            page_title="First Blog",
            raw_text="Learning Python is great. It is a fantastic programming language. I spent 2 hours debugging because I had a circular dependency.",
            author="Maya Chen",
            categories_tags=["Development", "Python"],
            page_type="blog post",
            readability_metrics={'flesch_reading_ease': 75.0, 'flesch_kincaid_grade': 6.5, 'gunning_fog': 8.0},
            sentiment_metrics={'polarity': 0.35, 'subjectivity': 0.5},
            ctas=["Learn More"],
            key_phrases=["learning python", "fantastic programming"],
            heading_structure=[{'level': 'h2', 'text': 'How to Start'}]
        )
        ScrapeResult.objects.create(
            website=self.website,
            page_url="https://testcoffee.com/blog/2",
            page_title="Second Blog",
            raw_text="Django is a web framework written in Python. It is fast and secure. We love building websites with it.",
            author="Maya Chen",
            categories_tags=["Development", "Django"],
            page_type="blog post",
            readability_metrics={'flesch_reading_ease': 65.0, 'flesch_kincaid_grade': 7.5, 'gunning_fog': 9.0},
            sentiment_metrics={'polarity': 0.15, 'subjectivity': 0.4},
            ctas=["Get Started"],
            key_phrases=["django web framework", "building websites"],
            heading_structure=[{'level': 'h2', 'text': 'Why Django?'}]
        )
        
        style_guide = build_advanced_style_guide(self.website.id)
        
        self.assertEqual(style_guide['common_authors'][0]['name'], "Maya Chen")
        self.assertEqual(style_guide['common_authors'][0]['count'], 2)
        self.assertEqual(style_guide['average_grade_level'], 7.0)
        self.assertEqual(style_guide['average_sentiment_polarity'], 0.25)
        self.assertIn("Development", style_guide['dominant_topics'])
        self.assertIn("Learn More", style_guide['call_to_action_examples'])
        
        # Verify it got saved to the website model
        self.website.refresh_from_db()
        self.assertIsNotNone(self.website.style_guide)
        self.assertEqual(self.website.style_guide['average_grade_level'], 7.0)

    def test_contact_and_logo_extraction(self):
        """Test that logo, email, and phone number extraction work correctly on HTML."""
        html = """
        <html>
            <head>
                <link rel="icon" href="/favicon.ico" />
                <link rel="apple-touch-icon" href="https://testcoffee.com/apple-icon.png" />
            </head>
            <body>
                <header>
                    <img src="/assets/images/brand-logo.png" class="main-logo" alt="Test Coffee Logo" />
                </header>
                <main>
                    <p>Contact us at info@testcoffee.com or call +1 555-019-2834 for help.</p>
                </main>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        res = _extract_from_soup(soup, "https://testcoffee.com", html)
        
        self.assertEqual(res['logo_url'], "https://testcoffee.com/assets/images/brand-logo.png")
        self.assertIn("info@testcoffee.com", res['scraped_emails'])
        self.assertIn("+1 555-019-2834", res['scraped_phones'])

    def test_save_logo_from_base64(self):
        """Test base64 logo saving utility."""
        from websites.crawler import save_logo_from_base64
        import os
        from django.conf import settings
        
        base64_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
        local_path = save_logo_from_base64(self.website, base64_data)
        
        self.assertTrue(local_path.startswith("/static/media/logos/logo_"))
        self.assertTrue(local_path.endswith(".png"))
        
        disk_path = os.path.join(settings.BASE_DIR, 'frontend', local_path.replace('/static/', ''))
        self.assertTrue(os.path.exists(disk_path))
        
        if os.path.exists(disk_path):
            try:
                os.remove(disk_path)
            except Exception:
                pass


from rest_framework.test import APITestCase


class WebsiteSoftDeleteAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testowner@cadence.io",
            username="testowner",
            password="testpassword",
            role="admin"
        )
        self.website = Website.objects.create(
            name="Test Coffee",
            domain="testcoffee.com",
            url="https://testcoffee.com",
            owner=self.user,
            status="active"
        )
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

    def test_list_excludes_deleted_by_default(self):
        # Soft delete the site
        self.website.is_deleted = True
        self.website.save()

        response = self.client.get('/api/websites/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_list_includes_deleted_when_trash_param(self):
        # Soft delete the site
        self.website.is_deleted = True
        self.website.save()

        response = self.client.get('/api/websites/?trash=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['id'], self.website.id)

    def test_delete_performs_soft_delete_by_default(self):
        response = self.client.delete(f'/api/websites/{self.website.id}/')
        self.assertEqual(response.status_code, 204)
        
        self.website.refresh_from_db()
        self.assertTrue(self.website.is_deleted)
        # Ensure it is NOT deleted from DB
        self.assertTrue(Website.objects.filter(id=self.website.id).exists())

    def test_delete_performs_hard_delete_with_hard_param(self):
        response = self.client.delete(f'/api/websites/{self.website.id}/?hard=true')
        self.assertEqual(response.status_code, 204)
        
        # Ensure it is deleted from DB
        self.assertFalse(Website.objects.filter(id=self.website.id).exists())

    def test_create_website_with_existing_active_domain_fails(self):
        data = {
            'name': 'New Site',
            'domain': 'testcoffee.com',
            'url': 'https://testcoffee.com',
            'industry': 'General',
            'tone': 'Professional',
            'topics': []
        }
        response = self.client.post('/api/websites/', data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('domain', response.json())

    def test_create_website_with_existing_soft_deleted_domain_succeeds(self):
        # Soft delete the existing site first
        self.website.is_deleted = True
        self.website.save()

        data = {
            'name': 'New Site',
            'domain': 'testcoffee.com',
            'url': 'https://testcoffee.com',
            'industry': 'General',
            'tone': 'Professional',
            'topics': []
        }
        response = self.client.post('/api/websites/', data, format='json')
        self.assertEqual(response.status_code, 201)
        
        # Verify the new website is created and active
        new_site_id = response.json()['id']
        new_site = Website.objects.get(id=new_site_id)
        self.assertFalse(new_site.is_deleted)
        
        # Verify the old soft-deleted website is hard-deleted to prevent conflict
        self.assertFalse(Website.objects.filter(id=self.website.id).exists())


class SecureConnectionsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="superuser@cadence.io",
            username="superuser",
            password="superpassword",
            role="super_admin"
        )
        self.website = Website.objects.create(
            name="Test Connections Cafe",
            domain="testconns.com",
            url="https://testconns.com",
            owner=self.user,
            status="active"
        )
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

    def test_encryption_decryption(self):
        """Test encryption and decryption utility helper."""
        from websites.utils import encrypt_value, decrypt_value
        val = "secret_api_key_12345"
        enc = encrypt_value(val)
        self.assertNotEqual(val, enc)
        dec = decrypt_value(enc)
        self.assertEqual(val, dec)

    def test_social_connection_serializer_encryption_and_masking(self):
        """Test that serializer encrypts auth payload on write and masks secrets on read."""
        url = f"/api/websites/{self.website.id}/social/"
        payload = {
            "platform": "blog",
            "make_webhook_url": "https://testconns.com/api/publish",
            "auth_type": "api_key",
            "auth_payload_write": {
                "api_key_name": "X-Auth-Token",
                "api_key_value": "super_secret_value_999"
            }
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        
        # Verify database value is encrypted
        conn = SocialConnection.objects.get(website=self.website, platform="blog")
        self.assertNotEqual(conn.auth_payload, "")
        self.assertNotIn("super_secret_value_999", conn.auth_payload)
        
        # Verify read response is masked
        response_data = response.json()
        self.assertEqual(response_data["auth_payload"]["api_key_name"], "X-Auth-Token")
        self.assertEqual(response_data["auth_payload"]["api_key_value"], "••••••••")

    def test_test_connection_view(self):
        """Test connection testing view endpoint."""
        url = f"/api/websites/{self.website.id}/social/blog/test/"
        payload = {
            "make_webhook_url": "https://httpbin.org/post",
            "auth_type": "bearer_token",
            "auth_payload_write": {
                "token_value": "test_bearer_token"
            }
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn("connected", response.json())
