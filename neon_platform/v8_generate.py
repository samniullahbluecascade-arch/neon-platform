"""
v8_generate.py  —  Gemini image-generation helpers for Neon Sign Studio
========================================================================

Phase 1  generate_mockup(...)                 → PNG bytes (colored neon mockup)
Phase 1' generate_mockup_with_judge(...)      → PNG bytes + judge log (retry loop)
Phase 2  generate_bw(mockup_bytes, ...)       → PNG bytes (binary tube centerlines)
Judge    judge_mockup(...)                    → dict (yes/no + failure modes)

Prompt construction is parametrised:
    sign_type ∈ {"standard"|"indoor", "outdoor", "rgb"}
    subtype   ∈ outdoor: pole_sign|monument_sign|wayfinding_sign|blade_sign|
                         standalone_sign|subway_sign|facade_storefront
              indoor:  living_room|cafe_bar|restaurant_booth|bedroom|
                       studio_office|retail_store_interior|barbershop|
                       tattoo_parlor|gym
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import time
from pathlib import Path

# ── Load .env (best-effort; falls back to OS env vars) ────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Prompt file paths (legacy — only B&W prompt still file-loaded) ───────────
_DIR = Path(__file__).parent

def _load_prompt(filename: str) -> str:
    try:
        return (_DIR / filename).read_text(encoding="utf-8")
    except Exception:
        return ""

_MOCKUP_TO_BW_PROMPT: str = _load_prompt("Mockup_to_B&W_prompt.txt")


# ─────────────────────────────────────────────────────────────────────────────
#  SUBTYPE TABLES — concrete scene clauses
# ─────────────────────────────────────────────────────────────────────────────

OUTDOOR_SUBTYPES = [
    "facade_storefront",
    "pole_sign",
    "monument_sign",
    "wayfinding_sign",
    "blade_sign",
    "standalone_sign",
    "subway_sign",
]

OUTDOOR_SUBTYPE_CLAUSES: dict = {
    "facade_storefront": {
        "scene": "Mounted flat on the brick or painted-stucco facade of an urban retail storefront. Sidewalk visible at the bottom of frame, one or two pedestrians passing softly out of focus, streetlamp glow and neighbouring shop fronts visible.",
        "housing": "an aluminum raceway bar bolted flush to the facade, painted to match the wall",
        "label": "Facade storefront",
    },
    "pole_sign": {
        "scene": "Housed in a rectangular weatherproof cabinet at the top of a four-meter galvanised steel pole anchored in concrete beside a roadway. Cars and tail-lights blur past on the road, treeline and dusk sky above.",
        "housing": "an aluminum cabinet with sealed seams atop a tapered steel pole",
        "label": "Pole sign",
    },
    "monument_sign": {
        "scene": "Set into a low landscaped stone-and-brick base at ground level at the entrance of a corporate campus or residential community. Manicured grass and ornamental shrubs around the base, a curving driveway behind, ground spotlights washing the base.",
        "housing": "a stone-clad base about one meter tall topped by an aluminum sign cabinet",
        "label": "Monument sign",
    },
    "wayfinding_sign": {
        "scene": "Mounted on a slim powder-coated steel post beside a paved walkway in a park, hospital campus, or university quad. Benches, planters, and the asphalt path visible alongside.",
        "housing": "a compact aluminum cabinet on a slim single-post mount",
        "label": "Wayfinding sign",
    },
    "blade_sign": {
        "scene": "Projecting perpendicularly from a storefront wall on a decorative wrought-iron or polished-aluminum arm, double-sided. The storefront facade, door and awning visible below at pedestrian-eye level.",
        "housing": "a double-sided cabinet on a perpendicular bracket arm extending from the wall",
        "label": "Blade/projection sign",
    },
    "standalone_sign": {
        "scene": "Freestanding on two legs on a concrete island in a parking lot or plaza. Cars parked behind, distant lamp posts and a low building skyline in the background, open sky overhead.",
        "housing": "a freestanding cabinet on two welded steel legs",
        "label": "Standalone sign",
    },
    "subway_sign": {
        "scene": "Mounted on the tiled wall of a subway or metro platform. Train tracks, platform edge, fluorescent strip-lit ceiling, and the corner of a metro train visible in the background.",
        "housing": "a flush wall-mounted weatherproof cabinet",
        "label": "Subway/transit sign",
    },
}

INDOOR_SUBTYPES = [
    "living_room",
    "cafe_bar",
    "restaurant_booth",
    "bedroom",
    "studio_office",
    "retail_store_interior",
    "barbershop",
    "tattoo_parlor",
    "gym",
]

INDOOR_SUBTYPE_CLAUSES: dict = {
    "living_room": {
        "scene": "Above the sofa in a modern living room. Wooden coffee table, throw pillows, indoor plant, and a soft lamp in the foreground; bookshelf and framed art on adjacent walls.",
        "label": "Living room",
    },
    "cafe_bar": {
        "scene": "Behind the espresso bar of a cafe. Exposed-brick wall as the sign background, pendant lights overhead, espresso machine, ceramic cups, and a barista's hand softly out of focus in the lower frame.",
        "label": "Cafe bar",
    },
    "restaurant_booth": {
        "scene": "Above a leather booth in a restaurant. Dark wood paneling on the walls, a table with cutlery, a candle, and water glasses in the foreground.",
        "label": "Restaurant booth",
    },
    "bedroom": {
        "scene": "Above the headboard of a queen bed in a modern bedroom. Linen sheets, a side lamp on a nightstand, and framed art on the adjacent wall.",
        "label": "Bedroom",
    },
    "studio_office": {
        "scene": "Above a wooden desk in a creative studio. A computer monitor, keyboard, indoor plant, stack of books, and warm pendant lighting in the foreground.",
        "label": "Studio / office",
    },
    "retail_store_interior": {
        "scene": "On the back wall of a boutique retail interior. Clothing racks, shelving, and merchandise softly out of focus in the foreground.",
        "label": "Retail store interior",
    },
    "barbershop": {
        "scene": "Above the mirror in a barbershop. Barber chair, vintage shaving tools on a counter, and tiled wall in the foreground.",
        "label": "Barbershop",
    },
    "tattoo_parlor": {
        "scene": "Above the entrance counter of a tattoo parlor. Posters, dark wood paneling, vinyl chair, and ink supplies in the foreground.",
        "label": "Tattoo parlor",
    },
    "gym": {
        "scene": "On the wall of a modern gym. Dumbbell rack, full-length mirror, and rubber flooring softly out of focus in the foreground.",
        "label": "Gym",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  PROMPT BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

_CONSTRUCTION_BLOCK = """SIGN CONSTRUCTION:
- Tubes: 12mm outer-diameter silicone LED neon flex. Constant 12mm thickness. Minimum bend radius about 50mm. Rounded sealed ends. Soft glow bloom around the tube — not razor-sharp.
- Tube color: matches the corresponding color in the uploaded design. Glow color equals tube color. Glow is the only light-emitting element on the sign.
- Tubes apply to: simple outlines, geometric strokes, lettering, icon outlines with minimum interior detail. No filled interiors, no shading, no clustered freeform.
- UV-printed elements: flat matte ink on the acrylic, no glow, visible as printed artwork. Apply UV print to complex multi-color regions, photo-real faces, dense small text under 8mm, fine gradients.
- UV and neon may coexist on the same sign. UV must be visually distinguishable — it does not glow.
- Black areas in the uploaded design may render as white neon tubes. Element shape, color, and position otherwise stay faithful to the uploaded design."""

_OUTPUT_BLOCK = """OUTPUT: ultra-high-resolution photograph. No watermarks, captions, dimension callouts, labels, or visible cables, stands, or power cords. The sign design (shape, layout, position and color of every element) matches the uploaded design exactly."""


def _format_extras(additional: str, uv: str) -> str:
    parts = []
    add = (additional or "").strip()
    uv_t = (uv or "").strip()
    if add:
        parts.append(f"ADDITIONAL INSTRUCTIONS (highest priority, override if conflict): {add}")
    if uv_t:
        parts.append(f"UV PRINTING INSTRUCTIONS (highest priority, override if conflict): {uv_t}")
    return "\n\n".join(parts) if parts else ""


def _prior_failure_block(prior_failure: str) -> str:
    if not prior_failure or not prior_failure.strip():
        return ""
    return (
        f"\n\nPRIOR ATTEMPT FAILED. Address every one of these problems:\n"
        f"- {prior_failure.strip()}\n"
    )


def _pick_subtype(sign_type: str, subtype: str | None) -> str:
    """Resolve subtype: explicit user choice → keep; else random from pool."""
    sign_type = (sign_type or "standard").lower()
    if sign_type == "outdoor":
        pool = OUTDOOR_SUBTYPES
        if subtype and subtype in OUTDOOR_SUBTYPE_CLAUSES:
            return subtype
        return random.choice(pool)
    # indoor / rgb / standard share indoor scene pool
    pool = INDOOR_SUBTYPES
    if subtype and subtype in INDOOR_SUBTYPE_CLAUSES:
        return subtype
    return random.choice(pool)


def _build_indoor_prompt(subtype: str, additional: str, uv: str, prior_failure: str = "") -> str:
    scene = INDOOR_SUBTYPE_CLAUSES[subtype]["scene"]
    extras = _format_extras(additional, uv)
    extras_block = f"\n\n{extras}" if extras else ""
    failure = _prior_failure_block(prior_failure)
    return f"""Photorealistic interior lifestyle photograph. Sony A7IV, 35mm lens, cinematic shallow depth of field. Camera faces the sign head-on with the sign face perpendicular to the optical axis. Aspect 4:3. The sign occupies 25 to 45 percent of the frame width.

ENVIRONMENT: {scene}

The room reads as a fully lived-in interior — furniture, props, materials, and human-scale objects all clearly visible. The sign is mounted flat on the back wall of the room above the main feature. Background props remain in soft focus and stay visually present; the wall does not fill the frame.

{_CONSTRUCTION_BLOCK}

LIGHTING: ambient room light is soft, dim, and warm. The neon glow is the dominant light source and color-matched spill lands on nearby surfaces and props. Other surfaces stay in natural shadow.

{_OUTPUT_BLOCK}{extras_block}{failure}"""


def _build_rgb_prompt(subtype: str, additional: str, uv: str, prior_failure: str = "") -> str:
    """Same as indoor but adds RGB-specific tube clause."""
    scene = INDOOR_SUBTYPE_CLAUSES[subtype]["scene"]
    extras = _format_extras(additional, uv)
    extras_block = f"\n\n{extras}" if extras else ""
    failure = _prior_failure_block(prior_failure)
    return f"""Photorealistic interior lifestyle photograph of an RGB / color-changing LED neon sign. Sony A7IV, 35mm lens, cinematic shallow depth of field. Camera faces the sign head-on with the sign face perpendicular to the optical axis. Aspect 4:3. The sign occupies 25 to 45 percent of the frame width.

ENVIRONMENT: {scene}

The room reads as a fully lived-in interior. The sign is mounted flat on the back wall of the room above the main feature. Background props remain in soft focus and stay visually present; the wall does not fill the frame.

{_CONSTRUCTION_BLOCK}

RGB BEHAVIOUR: this is an addressable RGB silicone neon flex sign. Show a frozen mid-cycle instant of the color animation — different letters, words, or segments of the design simultaneously display different colors (for example one letter cyan, the next magenta, the next amber). Diffuser silicone is very slightly milkier than single-color flex, giving a softer, slightly wider glow bloom. Where the uploaded design specifies a particular color, prefer that color but allow neighbouring elements to take complementary RGB hues to convey color-shifting.

LIGHTING: ambient room light is soft, dim, and warm. The RGB neon glow is the dominant light source; multiple glow colors gently spill onto nearby surfaces and props.

{_OUTPUT_BLOCK}{extras_block}{failure}"""


def _build_outdoor_prompt(subtype: str, additional: str, uv: str, prior_failure: str = "") -> str:
    info = OUTDOOR_SUBTYPE_CLAUSES[subtype]
    scene = info["scene"]
    housing = info["housing"]
    extras = _format_extras(additional, uv)
    extras_block = f"\n\n{extras}" if extras else ""
    failure = _prior_failure_block(prior_failure)
    return f"""Photorealistic outdoor environmental photograph at dusk (blue hour). Sony A7IV, 35mm lens, cinematic shallow depth of field. Camera faces the sign head-on with the sign face perpendicular to the optical axis. Aspect 16:9. The sign occupies 25 to 50 percent of the frame width.

LOCATION & SIGN-TYPE: this is a {info["label"]}. {scene}

The full outdoor environment is visible — sky, ground or pavement, vegetation, vehicles or pedestrians where appropriate, neighbouring structures. The scene is not a flat wall fill.

SIGN HOUSING: {housing}. The sign is built for outdoor exposure — IP65/IP67 weatherproof construction, sealed tube ends with visible protective silicone sheen.

SIGN CONSTRUCTION:
- Tubes: 12mm outer-diameter silicone LED neon flex, outdoor-rated variant. Constant 12mm thickness. Minimum bend radius about 50mm. Rounded sealed ends. Saturated outdoor-bright glow with soft bloom.
- Tube color: matches the corresponding color in the uploaded design. Glow color equals tube color. Glow is the only light-emitting element on the sign.
- Tubes apply to simple outlines, geometric strokes, and lettering. No filled interiors, no shading, no clustered freeform.
- UV-printed elements: flat matte ink on weather-resistant acrylic, no glow, visible as printed artwork. Apply UV print to complex multi-color regions, photo-real faces, dense small text under 8mm, fine gradients.
- UV and neon may coexist on the same sign. UV must be visually distinguishable — it does not glow.
- Black areas in the uploaded design may render as white neon tubes. Element shape, color, and position otherwise stay faithful to the uploaded design.

LIGHTING: dusk blue-hour ambient light. The neon glow is the dominant light source, color-matched to the tubes. Mild glow spill onto the immediate housing only.

{_OUTPUT_BLOCK}{extras_block}{failure}"""


def build_mockup_prompt(
    sign_type: str = "standard",
    subtype: str | None = None,
    additional: str = "",
    uv: str = "",
    prior_failure: str = "",
) -> tuple[str, str]:
    """
    Build the mockup-generation prompt. Returns (prompt_text, resolved_subtype).
    `resolved_subtype` reports which subtype was used (after random pick).
    """
    sign_type_l = (sign_type or "standard").lower()
    sub = _pick_subtype(sign_type_l, subtype)
    if sign_type_l == "outdoor":
        return _build_outdoor_prompt(sub, additional, uv, prior_failure), sub
    if sign_type_l == "rgb":
        return _build_rgb_prompt(sub, additional, uv, prior_failure), sub
    return _build_indoor_prompt(sub, additional, uv, prior_failure), sub


# ─────────────────────────────────────────────────────────────────────────────
#  GEMINI CLIENT / HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_MODEL_PHASE1 = "gemini-3-pro-image-preview"
_MODEL_PHASE2 = "gemini-3-pro-image-preview"
_MODEL_JUDGE  = "gemini-2.5-pro"

_MAX_RETRIES   = 3
_RETRY_DELAYS  = [3.0, 8.0, 20.0]


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. Set it in .env or the OS environment."
        )
    return key


def _make_client():
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from exc
    return genai.Client(api_key=_api_key())


def _to_png(raw: bytes, declared_mime: str = "image/png") -> bytes:
    from PIL import Image

    if declared_mime == "image/png":
        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()
            return raw
        except Exception:
            pass

    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _extract_image_from_response(response) -> bytes:
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

    reasons = [
        str(getattr(c, "finish_reason", "unknown"))
        for c in (response.candidates or [])
    ]
    # Surface SAFETY blocks so callers can stop retrying on copyrighted logos
    if any("SAFETY" in r.upper() or "BLOCK" in r.upper() for r in reasons):
        raise SafetyBlockedError(
            f"Gemini blocked the request on safety grounds. Finish reasons: {reasons}"
        )
    raise RuntimeError(
        f"Gemini returned no image. Finish reasons: {reasons or ['no candidates']}. "
        "Possible causes: safety filter, quota exceeded, or unsupported request."
    )


class SafetyBlockedError(RuntimeError):
    """Raised when Gemini blocks the request for safety / copyright reasons. Not retryable."""


def _call_gemini(client, parts: list, config, model: str) -> bytes:
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
        except SafetyBlockedError:
            raise  # never retry
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            retryable = any(
                tok in msg
                for tok in ("429", "quota", "resource_exhausted", "503", "unavailable", "returned no image")
            )
            if retryable and attempt < len(_RETRY_DELAYS):
                continue
            raise
    raise last_exc


# ─────────────────────────────────────────────────────────────────────────────
#  POST-PROCESSING (B&W binary)
# ─────────────────────────────────────────────────────────────────────────────

def postprocess_bw(png_bytes: bytes) -> bytes:
    import numpy as np
    from PIL import Image

    img  = Image.open(io.BytesIO(png_bytes)).convert("L")
    arr  = np.array(img, dtype=np.uint8)

    try:
        from skimage.filters import threshold_otsu
        if np.sum(arr > 0) > 100:
            thresh = int(threshold_otsu(arr[arr > 0]))
        else:
            thresh = int(threshold_otsu(arr))
    except (ImportError, ValueError):
        thresh = 127

    binary = (arr >= thresh).astype(np.uint8) * 255
    if np.sum(binary > 0) < 0.001 * arr.size:
        binary = (arr >= 40).astype(np.uint8) * 255

    try:
        import cv2
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    except ImportError:
        pass

    buf = io.BytesIO()
    Image.fromarray(binary, mode="L").save(buf, format="PNG")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API — generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_mockup(
    logo_bytes: bytes,
    logo_mime:  str,
    bg_bytes:   bytes | None = None,
    bg_mime:    str  | None  = None,
    additional: str          = "",
    uv:         str          = "",
    sign_type:  str          = "standard",
    subtype:    str | None   = None,
    prior_failure: str       = "",
) -> tuple[bytes, str, str]:
    """
    Phase 1 — Logo (+ optional background) → colored neon mockup.

    Returns:
        (png_bytes, resolved_subtype, prompt_text)
        - resolved_subtype: the subtype actually used (after random pick).
        - prompt_text: the final prompt sent to Gemini (for logging / judge feedback).

    Image ordering in parts (preserved):
      Part 0 : logo / design
      Part 1 : background (if supplied)
      Part 2 : prompt text
    """
    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from exc

    logo_png = _to_png(logo_bytes, logo_mime)

    prompt_text, resolved_subtype = build_mockup_prompt(
        sign_type=sign_type,
        subtype=subtype,
        additional=additional,
        uv=uv,
        prior_failure=prior_failure,
    )

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
    )

    raw = _call_gemini(client, parts, config, model=_MODEL_PHASE1)
    return _to_png(raw, "image/png"), resolved_subtype, prompt_text


def generate_bw(
    mockup_bytes: bytes,
    mockup_mime:  str = "image/png",
    additional:   str = "",
    uv:           str = "",
) -> bytes:
    """Phase 2 — Colored mockup → pure-white tube sketch on pure-black background."""
    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from exc

    mockup_png = _to_png(mockup_bytes, mockup_mime)

    base = _MOCKUP_TO_BW_PROMPT
    add_text = (additional or "").strip()
    uv_text  = (uv or "").strip()
    extras_lines = []
    if add_text:
        extras_lines.append(f"Additional Instructions: {add_text}")
    if uv_text:
        extras_lines.append(f"UV_PRINTING INSTRUCTIONS: {uv_text}")
    prompt_text = base
    if extras_lines:
        prompt_text = f"{base}\n\n" + "\n".join(extras_lines)
    # Legacy placeholder cleanup (the existing .txt has "[ ]" tokens)
    prompt_text = (prompt_text
                   .replace("Additional Instructions: [ ]", "")
                   .replace("UV_PRINTING INSTRUCTIONS: [ ]", ""))

    parts = [
        types.Part.from_bytes(data=mockup_png, mime_type="image/png"),
        prompt_text,
    ]

    client = _make_client()
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    )

    raw = _call_gemini(client, parts, config, model=_MODEL_PHASE2)
    png = _to_png(raw, "image/png")
    return postprocess_bw(png)


# ─────────────────────────────────────────────────────────────────────────────
#  JUDGE — VLM yes/no quality gate
# ─────────────────────────────────────────────────────────────────────────────

_JUDGE_RUBRIC_TEMPLATE = """You are a senior creative director reviewing a generated LED-neon-sign mockup before it is shown to a paying customer.

You are given:
  IMAGE 1 — the customer's uploaded design (source-of-truth shape / layout / colors).
  IMAGE 2 — the generated mockup that needs to be reviewed.

The intended sign category is: {sign_type_label}
The intended sub-environment is: {subtype_label}
The intended environment description is: "{scene_summary}"

Score the mockup on each axis below. The mockup passes overall only if EVERY axis passes.

A. SIGN FIDELITY — does the neon sign in image 2 match the uploaded design in image 1? Letter shapes, icon shapes, layout, proportions, colors all faithful? (Black areas in source may render as white tubes.)
B. ENVIRONMENT MATCH — does the surrounding scene match the intended sub-environment ("{subtype_label}")? For outdoor sub-environments the scene must show the outdoor location (street, pole, monument base, etc.), not a flat wall fill. For indoor sub-environments the scene must show recognisable indoor props (furniture, fixtures), not just a blank wall.
C. FRAMING — does the sign occupy roughly 25-55% of the frame width? Specifically the sign must NOT fill more than ~85% of the frame.
D. CONSTRUCTION PHYSICS — do the tubes look like real 12mm silicone LED neon flex? Constant thickness, smooth bends, sealed rounded ends, color-matched glow, no implausible freeform tangles?
E. NO ARTIFACTS — no watermarks, no captions, no dimension callouts, no visible power cords, stands or cables, no extra duplicate signs, no human faces overlapping the sign.
F. CAMERA — front-facing view, sign face roughly perpendicular to the camera, no exaggerated tilt or crop?

Return STRICT JSON exactly matching the schema. Field rules:
  axes        → object with keys A,B,C,D,E,F each "pass" or "fail"
  verdict     → "yes" if all six pass, otherwise "no"
  failure_modes → array of short concrete sentences (one per failing axis), telling the generator HOW to fix it next attempt. Empty if verdict is "yes".
  confidence  → number in [0,1], your confidence in this judgement.
"""

_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "axes": {
            "type": "object",
            "properties": {
                "A": {"type": "string", "enum": ["pass", "fail"]},
                "B": {"type": "string", "enum": ["pass", "fail"]},
                "C": {"type": "string", "enum": ["pass", "fail"]},
                "D": {"type": "string", "enum": ["pass", "fail"]},
                "E": {"type": "string", "enum": ["pass", "fail"]},
                "F": {"type": "string", "enum": ["pass", "fail"]},
            },
            "required": ["A", "B", "C", "D", "E", "F"],
        },
        "verdict": {"type": "string", "enum": ["yes", "no"]},
        "failure_modes": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": ["axes", "verdict", "failure_modes", "confidence"],
}


def _judge_labels(sign_type: str, subtype: str) -> tuple[str, str, str]:
    sign_type_l = (sign_type or "standard").lower()
    if sign_type_l == "outdoor":
        info = OUTDOOR_SUBTYPE_CLAUSES.get(subtype, {})
        return ("Outdoor sign", info.get("label", subtype), info.get("scene", ""))
    if sign_type_l == "rgb":
        info = INDOOR_SUBTYPE_CLAUSES.get(subtype, {})
        return ("RGB indoor sign", info.get("label", subtype), info.get("scene", ""))
    info = INDOOR_SUBTYPE_CLAUSES.get(subtype, {})
    return ("Indoor sign", info.get("label", subtype), info.get("scene", ""))


def judge_mockup(
    logo_bytes:   bytes,
    mockup_bytes: bytes,
    sign_type:    str,
    subtype:      str,
) -> dict:
    """
    Call gemini-2.5-pro vision to judge a generated mockup against the source design
    and the intended environment.

    Returns a dict matching _JUDGE_SCHEMA, with verdict in {"yes","no"}.
    Falls back to {"verdict":"yes", ...} if the judge call itself errors,
    so a flaky judge never blocks generation.
    """
    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai package not installed. Run: pip install google-genai"
        ) from exc

    sign_type_label, subtype_label, scene_summary = _judge_labels(sign_type, subtype)
    rubric = _JUDGE_RUBRIC_TEMPLATE.format(
        sign_type_label=sign_type_label,
        subtype_label=subtype_label,
        scene_summary=scene_summary,
    )

    logo_png   = _to_png(logo_bytes, "image/png")
    mockup_png = _to_png(mockup_bytes, "image/png")

    parts = [
        types.Part.from_bytes(data=logo_png,   mime_type="image/png"),
        types.Part.from_bytes(data=mockup_png, mime_type="image/png"),
        rubric,
    ]

    client = _make_client()
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=_JUDGE_SCHEMA,
        temperature=0.2,
    )

    try:
        response = client.models.generate_content(
            model=_MODEL_JUDGE,
            contents=parts,
            config=config,
        )
        raw = getattr(response, "text", None) or ""
        result = json.loads(raw)
        # Normalise / sanity-check
        if "verdict" not in result:
            result["verdict"] = "yes"  # benefit-of-doubt
        if "failure_modes" not in result:
            result["failure_modes"] = []
        if "confidence" not in result:
            result["confidence"] = 0.5
        return result
    except Exception as exc:
        # Never let a flaky judge block the generation; accept the mockup.
        return {
            "verdict": "yes",
            "failure_modes": [],
            "confidence": 0.0,
            "judge_error": str(exc),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  GENERATE + JUDGE LOOP
# ─────────────────────────────────────────────────────────────────────────────

def generate_mockup_with_judge(
    logo_bytes: bytes,
    logo_mime:  str,
    bg_bytes:   bytes | None = None,
    bg_mime:    str  | None  = None,
    additional: str          = "",
    uv:         str          = "",
    sign_type:  str          = "standard",
    subtype:    str | None   = None,
    max_retries: int         = 0,
) -> dict:
    """
    Generate a mockup with an optional judge-loop retry.

    max_retries = 0  → single pass, no judging, identical cost to old generate_mockup.
    max_retries > 0  → judge each output; on "no", regenerate with prior-failure
                       feedback injected. Cap at max_retries extra attempts.

    Returns:
        {
            "mockup_bytes":    bytes,
            "subtype":         str,    # resolved subtype
            "attempts":        int,    # total mockup generations (>= 1)
            "judge_calls":     int,    # total judge invocations
            "gemini_calls":    int,    # attempts + judge_calls (for billing/usage)
            "judge_log":       list,   # per-attempt {verdict, failure_modes, confidence, judge_error?}
            "final_verdict":   "yes" | "no" | "unjudged",
            "prompt":          str,    # final prompt sent (for telemetry)
        }
    """
    judge_log: list = []
    last_failure = ""
    last_mockup: bytes | None = None
    last_subtype = subtype or ""
    last_prompt = ""
    attempts = 0
    judge_calls = 0
    last_judgment: dict | None = None

    total_passes = 1 + max(0, int(max_retries))

    for attempt_idx in range(total_passes):
        feedback = last_failure if attempt_idx > 0 else ""
        try:
            mockup_bytes, resolved_subtype, prompt_text = generate_mockup(
                logo_bytes=logo_bytes,
                logo_mime=logo_mime,
                bg_bytes=bg_bytes,
                bg_mime=bg_mime,
                additional=additional,
                uv=uv,
                sign_type=sign_type,
                subtype=subtype,
                prior_failure=feedback,
            )
        except SafetyBlockedError:
            # Logo / design tripped Gemini safety — no point retrying.
            raise
        attempts += 1
        last_mockup = mockup_bytes
        last_subtype = resolved_subtype
        last_prompt = prompt_text

        # No judging requested → accept first output.
        if max_retries <= 0:
            judge_log.append({"attempt": attempt_idx, "skipped": True})
            return {
                "mockup_bytes": mockup_bytes,
                "subtype": resolved_subtype,
                "attempts": attempts,
                "judge_calls": 0,
                "gemini_calls": attempts,
                "judge_log": judge_log,
                "final_verdict": "unjudged",
                "prompt": prompt_text,
            }

        judgment = judge_mockup(
            logo_bytes=logo_bytes,
            mockup_bytes=mockup_bytes,
            sign_type=sign_type,
            subtype=resolved_subtype,
        )
        judge_calls += 1
        judge_log.append({
            "attempt": attempt_idx,
            "subtype": resolved_subtype,
            **judgment,
        })
        last_judgment = judgment

        if judgment.get("verdict") == "yes":
            return {
                "mockup_bytes": mockup_bytes,
                "subtype": resolved_subtype,
                "attempts": attempts,
                "judge_calls": judge_calls,
                "gemini_calls": attempts + judge_calls,
                "judge_log": judge_log,
                "final_verdict": "yes",
                "prompt": prompt_text,
            }

        # Low judge confidence on "no" → don't trust the rejection, accept.
        if float(judgment.get("confidence", 0.0)) < 0.6:
            return {
                "mockup_bytes": mockup_bytes,
                "subtype": resolved_subtype,
                "attempts": attempts,
                "judge_calls": judge_calls,
                "gemini_calls": attempts + judge_calls,
                "judge_log": judge_log,
                "final_verdict": "no_low_confidence",
                "prompt": prompt_text,
            }

        # Stage feedback for next loop iteration.
        last_failure = "; ".join(judgment.get("failure_modes", []) or [])

    # Exhausted retries → return last mockup with a "no" verdict so caller can warn user.
    return {
        "mockup_bytes": last_mockup or b"",
        "subtype": last_subtype,
        "attempts": attempts,
        "judge_calls": judge_calls,
        "gemini_calls": attempts + judge_calls,
        "judge_log": judge_log,
        "final_verdict": (last_judgment or {}).get("verdict", "no"),
        "prompt": last_prompt,
    }
