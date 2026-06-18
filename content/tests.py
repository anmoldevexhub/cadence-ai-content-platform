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
