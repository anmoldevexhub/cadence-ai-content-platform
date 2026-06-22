from django.test import TestCase
from websites.models import Website
from django.contrib.auth import get_user_model
from content.generator import build_svg_from_data

User = get_user_model()

class ContentGeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testcontent@cadence.io",
            username="testcontent",
            password="testpassword",
            role="admin"
        )
        self.website = Website.objects.create(
            name="Test Bakery",
            domain="testbakery.com",
            url="https://testbakery.com",
            owner=self.user,
            contact_email="bakery@test.com",
            contact_phone="+1 123-456-7890",
            logo_url=""
        )

    def test_build_svg_from_data_custom_footer(self):
        """Test that build_svg_from_data generates the SVG containing the website's dynamic footer."""
        data = {
            "theme": "theme1",
            "title_lines": [{"text": "Fresh Bread", "type": "plain"}],
            "subtext": "Fresh bread daily.",
            "cta_text": "ORDER NOW",
            "laptop_screen": {"title": "BAKERY", "subtitle": "Dashboard"},
            "badges": [{"label": "Sourdough", "color": "#ff0000"}]
        }
        
        svg = build_svg_from_data(data, website=self.website)
        
        self.assertIn("bakery@test.com", svg)
        self.assertIn("+1 123-456-7890", svg)
        self.assertIn("testbakery.com", svg)
        
    def test_build_svg_from_data_empty_phone(self):
        """Test that footer adjusts gracefully when phone number is empty."""
        self.website.contact_phone = ""
        self.website.save()
        
        data = {
            "theme": "theme1",
            "title_lines": [{"text": "Fresh Bread", "type": "plain"}],
            "subtext": "Fresh bread daily.",
            "cta_text": "ORDER NOW",
            "laptop_screen": {"title": "BAKERY", "subtitle": "Dashboard"},
            "badges": [{"label": "Sourdough", "color": "#ff0000"}]
        }
        
        svg = build_svg_from_data(data, website=self.website)
        
        self.assertNotIn("+1 123-456-7890", svg)
        self.assertIn("bakery@test.com", svg)
        self.assertIn("testbakery.com", svg)


from websites.models import SampleContent
from content.generator import get_style_reference_samples, build_system_prompt

class SampleContentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testsample@cadence.io",
            username="testsample",
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
    def test_get_style_reference_samples_empty(self):
        """Test returning default text when no samples exist."""
        samples_text = get_style_reference_samples(self.website, 'blog')
        self.assertEqual(samples_text, "No samples or crawled content available. Please upload sample content or crawl the website first.")

    def test_get_style_reference_samples_populated(self):
        """Test returning formatted samples text."""
        # Create active samples
        SampleContent.objects.create(
            website=self.website,
            platform='blog',
            title='Sample 1',
            content='This is some sample content for blog.',
            file_name='sample1.txt',
            is_active=True
        )
        SampleContent.objects.create(
            website=self.website,
            platform='blog',
            title='Sample 2',
            content='Another sample content here.',
            file_name='sample2.txt',
            is_active=True
        )
        # Create inactive sample
        SampleContent.objects.create(
            website=self.website,
            platform='blog',
            title='Sample 3',
            content='Inactive sample.',
            file_name='sample3.txt',
            is_active=False
        )

        samples_text = get_style_reference_samples(self.website, 'blog')
        self.assertIn("SAMPLE 1 (BLOG):", samples_text)
        self.assertIn("SAMPLE 2 (BLOG):", samples_text)
        self.assertNotIn("SAMPLE 3", samples_text)
        self.assertIn("This is some sample content for blog.", samples_text)
        self.assertIn("Another sample content here.", samples_text)

    def test_build_system_prompt(self):
        """Test minimal system prompt structure."""
        SampleContent.objects.create(
            website=self.website,
            platform='blog',
            title='Test Blog Sample',
            content='Sample blog content.',
            is_active=True
        )
        prompt = build_system_prompt(self.website)
        self.assertIn(self.website.name, prompt)
        self.assertIn("Write in the same style as the samples", prompt)


from rest_framework.test import APITestCase
from content.models import ContentDraft


class ContentDraftSoftDeleteAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testsample@cadence.io",
            username="testsample",
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
        self.draft = ContentDraft.objects.create(
            website=self.website,
            platform='blog',
            title='Sample Draft',
            body='Some body content',
            status='draft'
        )
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

    def test_list_excludes_deleted_by_default(self):
        self.draft.is_deleted = True
        self.draft.save()

        response = self.client.get('/api/content/drafts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_list_includes_deleted_when_trash_param(self):
        self.draft.is_deleted = True
        self.draft.save()

        response = self.client.get('/api/content/drafts/?trash=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['id'], self.draft.id)

    def test_delete_performs_soft_delete_by_default(self):
        response = self.client.delete(f'/api/content/drafts/{self.draft.id}/')
        self.assertEqual(response.status_code, 204)

        self.draft.refresh_from_db()
        self.assertTrue(self.draft.is_deleted)
        self.assertTrue(ContentDraft.objects.filter(id=self.draft.id).exists())

    def test_delete_performs_hard_delete_with_hard_param(self):
        response = self.client.delete(f'/api/content/drafts/{self.draft.id}/?hard=true')
        self.assertEqual(response.status_code, 204)

        self.assertFalse(ContentDraft.objects.filter(id=self.draft.id).exists())

    def test_update_draft_with_base64_cover_image(self):
        import os
        from django.conf import settings
        
        # 1x1 pixel PNG image base64 encoded
        base64_png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        payload = {
            "title": "Updated Draft Title",
            "cover_image": base64_png
        }
        
        response = self.client.patch(f'/api/content/drafts/{self.draft.id}/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        cover_image_url = data.get('cover_image')
        self.assertTrue(cover_image_url.startswith('/static/media/covers/cover_'))
        self.assertTrue(cover_image_url.endswith('.png'))
        
        # Verify the file is actually written to disk
        filename = cover_image_url.split('/')[-1]
        filepath = os.path.join(settings.BASE_DIR, 'frontend', 'media', 'covers', filename)
        self.assertTrue(os.path.exists(filepath))
        
        # Clean up the file
        if os.path.exists(filepath):
            os.remove(filepath)

    def test_update_draft_with_custom_metadata(self):
        payload = {
            "title": "Custom Metadata Draft",
            "author_name": "Jane Doe",
            "custom_date": "July 4, 1776",
            "category": "History"
        }
        response = self.client.patch(f'/api/content/drafts/{self.draft.id}/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.author_name, "Jane Doe")
        self.assertEqual(self.draft.custom_date, "July 4, 1776")
        self.assertEqual(self.draft.category, "History")
