"""
v8_generate.py  —  Gemini image-generation helpers for Neon Sign Studio
========================================================================

Phase 1  generate_mockup(logo_bytes, logo_mime, bg_bytes, bg_mime, additional)
         → PNG bytes   Photorealistic colored LED neon sign mounted on background.

Phase 2  generate_bw(mockup_bytes, mockup_mime)
         → PNG bytes   Pure-white tube centerlines on pure-black background
                       (post-processed to strict binary for LOC pipeline).
"""

from __future__ import annotations

import base64
import io
import os
import time
from pathlib import Path

# ── Load .env (best-effort; falls back to OS env vars) ────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Prompt file paths ─────────────────────────────────────────────────────────
_DIR = Path(__file__).parent

try:
    _LOGO_TO_MOCKUP_PROMPT: str = (
        (_DIR / "logo_to_mockup_prompt.txt").read_text(encoding="utf-8")
    )
except Exception:
    _LOGO_TO_MOCKUP_PROMPT = ""
try:
    _MOCKUP_TO_BW_PROMPT: str = (
        (_DIR / "Mockup_to_B&W_prompt.txt").read_text(encoding="utf-8")
    )
except Exception:
    _MOCKUP_TO_BW_PROMPT = ""

# Placeholder in logo_to_mockup_prompt.txt for additional instructions
_ADDITIONAL_PLACEHOLDER = "[ ]"

# Gemini models — both confirmed to support multimodal-in + image-out
_MODEL_PHASE1 = "gemini-3-pro-image-preview"      # Phase 1: photorealistic creative generation
_MODEL_PHASE2 = "gemini-3-pro-image-preview"           # Phase 2: precise extraction (postprocessed anyway)

# Retry config for quota / transient errors
_MAX_RETRIES   = 3
_RETRY_DELAYS  = [3.0, 8.0, 20.0]   # seconds between attempts


# ── Helpers ───────────────────────────────────────────────────────────────────

def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. Set it in .env or the OS environment."
        )
    return key


def _make_client():
    """Return an authenticated google-genai Client."""
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from exc
    return genai.Client(api_key=_api_key())


def _to_png(raw: bytes, declared_mime: str = "image/png") -> bytes:
    """
    Ensure image is valid PNG.  Converts JPEG / WebP / BMP / etc. via Pillow.
    Preserves PNG as-is after quick validity check.
    """
    from PIL import Image

    if declared_mime == "image/png":
        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()          # will raise on corrupt data
            return raw            # already valid PNG
        except Exception:
            pass                  # fall through to re-encode

    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _extract_image_from_response(response) -> bytes:
    """
    Pull the first image blob out of a Gemini GenerateContent response.
    Handles both raw-bytes and base64-string data fields.
    Raises RuntimeError with finish reasons on failure.
    """
    for candidate in (response.candidates or []):
        for part in getattr(candidate.content, "parts", []) or []:
            idata = getattr(part, "inline_data", None)
            if idata is None:
                continue
            data = getattr(idata, "data", None)
            if data is None:
                continue
            if isinstance(data, str):
                data = base64.b64decode(data)
            if data:
                return bytes(data)

    # Build an informative error
    reasons = [
        str(getattr(c, "finish_reason", "unknown"))
        for c in (response.candidates or [])
    ]
    raise RuntimeError(
        f"Gemini returned no image. Finish reasons: {reasons or ['no candidates']}. "
        "Possible causes: safety filter, quota exceeded, or unsupported request."
    )


def _call_gemini(client, parts: list, config, model: str) -> bytes:
    """
    Call Gemini generate_content with exponential-backoff retry on
    rate-limit (429) and transient server (5xx) errors.
    """
    last_exc: Exception = RuntimeError("No attempt made")

    for attempt, delay in enumerate([0.0] + _RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            response = client.models.generate_content(
                model=model,
                contents=parts,
                config=config,
            )
            return _extract_image_from_response(response)

        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            # Retry on rate limits (429), quota, transient server (5xx),
            # AND "Gemini returned no image" (which might be a transient generation failure)
            retryable = any(
                tok in msg
                for tok in ("429", "quota", "resource_exhausted", "503", "unavailable", "returned no image")
            )
            if retryable and attempt < len(_RETRY_DELAYS):
                continue   # retry with next delay
            raise

    raise last_exc


# ── Post-processing: enforce strict binary for LOC pipeline ───────────────────

def postprocess_bw(png_bytes: bytes) -> bytes:
    """
    Harden the Phase-2 B&W output so the LOC pipeline sees a clean signal:

      1. Convert to grayscale
      2. Otsu global threshold  →  {0, 255}  strict binary
      3. Morphological CLOSE (3×3) to bridge single-pixel gaps in tubes
         without dilating (tube width preserved)
      4. Re-encode as PNG

    Falls back gracefully: if scikit-image is absent, uses a fixed
    threshold of 127 instead of Otsu.
    """
    import numpy as np
    from PIL import Image

    img  = Image.open(io.BytesIO(png_bytes)).convert("L")
    arr  = np.array(img, dtype=np.uint8)

    # Threshold selection
    try:
        from skimage.filters import threshold_otsu
        # Apply Otsu to non-zero pixels only if possible to get better separation
        if np.sum(arr > 0) > 100:
            thresh = int(threshold_otsu(arr[arr > 0]))
        else:
            thresh = int(threshold_otsu(arr))
    except (ImportError, ValueError):
        thresh = 127

    # Guard: if threshold is too high (almost no white pixels), fall back
    binary = (arr >= thresh).astype(np.uint8) * 255
    if np.sum(binary > 0) < 0.001 * arr.size:
        # Fall back to a fixed low threshold to capture any signal
        binary = (arr >= 40).astype(np.uint8) * 255

    # Morphological close (3×3 rect) — bridges single-pixel gaps
    try:
        import cv2
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    except ImportError:
        pass   # opencv optional; binary is already usable without closing

    buf = io.BytesIO()
    Image.fromarray(binary, mode="L").save(buf, format="PNG")
    return buf.getvalue()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_mockup(
    logo_bytes: bytes,
    logo_mime:  str,
    bg_bytes:   bytes | None = None,
    bg_mime:    str  | None  = None,
    additional: str          = "",
) -> bytes:
    """
    Phase 1 — Logo (+ optional background environment) → colored neon mockup.

    Image ordering matches the prompt contract:
      Part 0 : logo / design  (Image 1 in prompt)
      Part 1 : background     (Image 2 in prompt, if supplied)
      Part 2 : prompt text

    Returns PNG bytes.
    """
    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from exc

    logo_png = _to_png(logo_bytes, logo_mime)

    # Substitute the n8n placeholder with actual additional instructions
    if _ADDITIONAL_PLACEHOLDER in _LOGO_TO_MOCKUP_PROMPT:
        prompt_text = _LOGO_TO_MOCKUP_PROMPT.replace(
            _ADDITIONAL_PLACEHOLDER,
            additional.strip() if additional.strip() else "None",
        )
    else:
        # Fallback: append at the end
        prompt_text = _LOGO_TO_MOCKUP_PROMPT + "\n\nADDITIONAL INSTRUCTIONS:\n" + (additional.strip() if additional.strip() else "None")

    parts: list = [
        types.Part.from_bytes(data=logo_png, mime_type="image/png"),
    ]
    if bg_bytes:
        bg_png = _to_png(bg_bytes, bg_mime or "image/jpeg")
        parts.append(types.Part.from_bytes(data=bg_png, mime_type="image/png"))
    parts.append(prompt_text)

    client = _make_client()
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="OFF"),
        ]
    )

    raw = _call_gemini(client, parts, config, model=_MODEL_PHASE1)
    return _to_png(raw, "image/png")


def generate_bw(
    mockup_bytes: bytes,
    mockup_mime:  str = "image/png",
    additional:   str = "",
) -> bytes:
    """
    Phase 2 — Colored mockup → pure-white tube sketch on pure-black background.

    Post-processes the Gemini output to strict binary (Otsu + morph close)
    before returning, so the V8 LOC pipeline receives a clean B&W image.

    Args:
        mockup_bytes: The colored mockup image bytes
        mockup_mime: MIME type of the mockup image
        additional: Optional additional instructions for the B&W conversion

    Returns PNG bytes.
    """
    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from exc

    mockup_png = _to_png(mockup_bytes, mockup_mime)

    # Substitute the placeholder with actual additional instructions
    if _ADDITIONAL_PLACEHOLDER in _MOCKUP_TO_BW_PROMPT:
        prompt_text = _MOCKUP_TO_BW_PROMPT.replace(
            _ADDITIONAL_PLACEHOLDER,
            additional.strip() if additional.strip() else "None",
        )
    else:
        # Fallback: append at the end
        prompt_text = _MOCKUP_TO_BW_PROMPT + "\n\nADDITIONAL INSTRUCTIONS:\n" + (additional.strip() if additional.strip() else "None")

    parts = [
        types.Part.from_bytes(data=mockup_png, mime_type="image/png"),
        prompt_text,
    ]

    client = _make_client()
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="OFF"),
        ]
    )

    raw = _call_gemini(client, parts, config, model=_MODEL_PHASE2)
    png = _to_png(raw, "image/png")
    return postprocess_bw(png)
