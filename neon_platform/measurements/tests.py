from django.urls import reverse
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
import base64
import io
import json
import unittest
from unittest.mock import patch


# A real Pillow-generated PNG (32x32 black) so Django's ImageField passes
# Pillow's verify(). Using a hand-crafted 1x1 PNG can fail ImageField on
# some Pillow versions, producing spurious 400s.
def _make_valid_png(size: int = 32) -> bytes:
    from PIL import Image
    img = Image.new("RGB", (size, size), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


PNG_DATA = _make_valid_png(32)


# Stub Gemini callers so unit tests don't hit the real API.
def _stub_mockup_with_judge(**kwargs):
    return {
        "mockup_bytes": PNG_DATA,
        "subtype": kwargs.get("subtype") or "living_room",
        "attempts": 1,
        "judge_calls": 0,
        "gemini_calls": 1,
        "judge_log": [{"attempt": 0, "skipped": True}],
        "final_verdict": "unjudged",
        "prompt": "stub-prompt",
    }


def _stub_bw(mockup_bytes, mime="image/png", additional="", uv=""):
    return PNG_DATA


@override_settings(MEDIA_ROOT="/tmp/django_test_media/")
class V8APITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="tester@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.logo_file = SimpleUploadedFile(
            "logo.png", PNG_DATA, content_type="image/png"
        )
        self.bg_file = SimpleUploadedFile(
            "bg.png", PNG_DATA, content_type="image/png"
        )

    @patch("measurements.views.generate_mockup_with_judge", side_effect=_stub_mockup_with_judge)
    def test_generate_mockup(self, _mock):
        url = reverse("generate_mockup")
        response = self.client.post(
            url,
            {
                "logo": self.logo_file,
                "background": self.bg_file,
                "additional": "test",
                "sign_type": "standard",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("image_b64", body)
        self.assertEqual(body.get("sign_type"), "standard")
        self.assertIn("subtype", body)

    @patch("measurements.views.generate_mockup_with_judge", side_effect=_stub_mockup_with_judge)
    def test_generate_mockup_outdoor_with_subtype(self, _mock):
        url = reverse("generate_mockup")
        response = self.client.post(
            url,
            {
                "logo": self.logo_file,
                "sign_type": "outdoor",
                "subtype": "pole_sign",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("sign_type"), "outdoor")

    @patch("measurements.views.generate_bw", side_effect=_stub_bw)
    def test_generate_bw(self, _mock):
        mockup_file = SimpleUploadedFile(
            "mockup.png", PNG_DATA, content_type="image/png"
        )
        url = reverse("generate_bw")
        response = self.client.post(
            url,
            {"mockup": mockup_file, "additional": "test"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("image_b64", response.json())

    @patch("measurements.views.generate_bw", side_effect=_stub_bw)
    @patch("measurements.views.generate_mockup_with_judge", side_effect=_stub_mockup_with_judge)
    def test_full_pipeline(self, _mg, _bw):
        url = reverse("full_pipeline")
        response = self.client.post(
            url,
            {
                "logo": self.logo_file,
                "background": self.bg_file,
                "width_inches": "1.0",
                "height_inches": "1.0",
                "additional": "test",
                "sign_type": "outdoor",
                "subtype": "monument_sign",
                "force_format": "",
                "ground_truth_m": "",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn("mockup_b64", result)
        self.assertIn("bw_b64",     result)
        self.assertIn("measurement", result)
        self.assertEqual(result.get("sign_type"), "outdoor")
        self.assertEqual(result.get("subtype"),   "monument_sign")
        self.assertIn("final_verdict", result)

    @patch("measurements.views.generate_bw", side_effect=_stub_bw)
    def test_bw_only_pipeline(self, _mock):
        mockup_file = SimpleUploadedFile(
            "mockup.png", PNG_DATA, content_type="image/png"
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
        body = response.json()
        self.assertIn("bw_b64",      body)
        self.assertIn("measurement", body)

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

    @unittest.skip(
        "Requires Ground_Truth folder present at V8_ENGINE_PATH — "
        "env-dependent, skip in CI."
    )
    def test_evaluate(self):
        url = reverse("evaluate")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        try:
            json.loads(response.content)
        except json.JSONDecodeError:
            self.fail("Evaluate endpoint did not return valid JSON")

    # ── Auth lock smoke tests — unauthenticated clients must be rejected ─────
    def test_unauthenticated_blocked_on_generate_mockup(self):
        anon = APIClient()
        url = reverse("generate_mockup")
        response = anon.post(url, {"logo": self.logo_file}, format="multipart")
        self.assertIn(response.status_code, (401, 403))

    def test_unauthenticated_blocked_on_full_pipeline(self):
        anon = APIClient()
        url = reverse("full_pipeline")
        response = anon.post(
            url,
            {"logo": self.logo_file, "width_inches": "1.0"},
            format="multipart",
        )
        self.assertIn(response.status_code, (401, 403))
