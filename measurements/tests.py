from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
import base64
import json

# Simple 1x1 PNG image (transparent) for testing uploads
PNG_DATA = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAn8B9pVYVQAAAABJRU5ErkJggg=="
)

@override_settings(MEDIA_ROOT="/tmp/django_test_media/")
class V8APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a simple uploaded file for logo/background
        self.logo_file = SimpleUploadedFile(
            "logo.png", PNG_DATA, content_type="image/png"
        )
        self.bg_file = SimpleUploadedFile(
            "bg.png", PNG_DATA, content_type="image/png"
        )

    def test_generate_mockup(self):
        url = reverse("generate_mockup")
        response = self.client.post(
            url,
            {
                "logo": self.logo_file,
                "background": self.bg_file,
                "additional": "test",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("image_b64", response.json())

    def test_generate_bw(self):
        # First generate a mockup to use as input
        mockup_resp = self.client.post(
            reverse("generate_mockup"),
            {"logo": self.logo_file},
            format="multipart",
        )
        self.assertEqual(mockup_resp.status_code, 200)
        mockup_b64 = mockup_resp.json()["image_b64"]
        mockup_file = SimpleUploadedFile(
            "mockup.png",
            base64.b64decode(mockup_b64),
            content_type="image/png",
        )
        url = reverse("generate_bw")
        response = self.client.post(
            url,
            {"mockup": mockup_file, "additional": "test"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("image_b64", response.json())

    def test_full_pipeline(self):
        url = reverse("full_pipeline")
        response = self.client.post(
            url,
            {
                "logo": self.logo_file,
                "background": self.bg_file,
                "width_inches": "1.0",
                "height_inches": "1.0",
                "additional": "test",
                "force_format": "",
                "ground_truth_m": "",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        # Expect a dict with many result fields
        result = response.json()
        self.assertIn("measured_m", result)
        self.assertIn("overlay_b64", result)

    def test_bw_only_pipeline(self):
        # Generate a mockup first
        mockup_resp = self.client.post(
            reverse("generate_mockup"),
            {"logo": self.logo_file},
            format="multipart",
        )
        self.assertEqual(mockup_resp.status_code, 200)
        mockup_b64 = mockup_resp.json()["image_b64"]
        mockup_file = SimpleUploadedFile(
            "mockup.png",
            base64.b64decode(mockup_b64),
            content_type="image/png",
        )
        url = reverse("bw_only_pipeline")
        response = self.client.post(
            url,
            {
                "mockup": mockup_file,
                "width_inches": "1.0",
                "height_inches": "1.0",
                "additional": "test",
                "force_format": "",
                "ground_truth_m": "",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("measured_m", response.json())

    def test_measure(self):
        url = reverse("measure")
        response = self.client.post(
            url,
            {
                "image": self.logo_file,
                "width_inches": "1.0",
                "height_inches": "1.0",
                "force_format": "",
                "ground_truth_m": "",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("measured_m", response.json())

    def test_evaluate(self):
        url = reverse("evaluate")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Evaluation returns a dict or list; ensure JSON is parseable
        try:
            json.loads(response.content)
        except json.JSONDecodeError:
            self.fail("Evaluate endpoint did not return valid JSON")