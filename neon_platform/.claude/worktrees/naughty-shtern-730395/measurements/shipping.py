"""
Shipping cost computation for sign delivery.

Calls the EpicCraftings shipping calculator with dimensions derived from:
  - user-supplied sign width (inches) → API "length" = width + 3
  - aspect ratio of the BW sign bounding box → API "width" = (width / aspect) + 1
  - constant API "height" = 0.75

Returns totalShipmentCost of the cheapest carrier (data[0]) or None on failure.
"""
from __future__ import annotations

import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Static config — token + endpoint provided by ops
_SHIPPING_URL = "https://ecship-admin.epiccraftings.com/api/shipping/calculation"
_SHIPPING_TOKEN = (
    "fj8924u35r89jr02uj3c50328j94c2347j3298c4738974890273j47304j89237jc7c4897348"
)


def compute_bbox_aspect_ratio(bw_bytes: bytes, threshold: int = 30) -> float:
    """
    Aspect ratio (width/height) of the bounding box of the non-black tubes
    in a BW sign image. Defaults to 1.0 if the image is empty.
    """
    try:
        import numpy as np
        from PIL import Image

        img = np.array(Image.open(io.BytesIO(bw_bytes)).convert("L"))
        mask = img > threshold
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        if not rows.any() or not cols.any():
            return 1.0
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        bbox_w = max(1, int(cmax - cmin + 1))
        bbox_h = max(1, int(rmax - rmin + 1))
        return bbox_w / bbox_h
    except Exception as exc:
        logger.warning("compute_bbox_aspect_ratio failed: %s", exc)
        return 1.0


def compute_box_dims(width_inches: float, bw_bytes: bytes) -> Tuple[float, float, float]:
    """
    Returns (length, width, height) in inches for the shipping API payload.
    """
    aspect = compute_bbox_aspect_ratio(bw_bytes)
    real_height_in = width_inches / aspect if aspect > 0 else width_inches
    length = round(float(width_inches) + 3.0, 2)
    width  = round(real_height_in + 1.0, 2)
    height = 0.75
    return length, width, height


def get_shipping_cost(
    width_inches: float,
    bw_bytes: bytes,
    timeout: float = 12.0,
) -> Optional[float]:
    """
    Returns totalShipmentCost (USD) of the cheapest carrier from the
    EpicCraftings shipping API, or None if the call fails.

    Never raises — shipping failure must not block the measurement pipeline.
    """
    try:
        import requests
    except ImportError:
        logger.warning("requests not installed; skipping shipping cost.")
        return None

    length, width, height = compute_box_dims(width_inches, bw_bytes)

    payload = {
        "destinationAddress": {
            "country": "US",
            "countryName": "United States",
            "zip": "",
            "declaredValue": "",
            "declaredCountryCode": "USD",
            "criteria": "cheapest",
            "dutyService": "Default DAP",
        },
        "productSpecs": {
            "units": "inches",
            "rushDelivery": False,
            "careerDDP": False,
            "dimension": "box",
            "boxes": [
                {
                    "size": {"length": length, "width": width, "height": height},
                    "quantity": 1,
                    "denseWeight": "0.5",
                }
            ],
        },
    }
    headers = {
        "Authorization": f"Bearer {_SHIPPING_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(_SHIPPING_URL, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        body = r.json()
        carriers = body.get("data") or []
        if not carriers:
            logger.warning("Shipping API returned empty data array.")
            return None
        cost = carriers[0].get("totalShipmentCost")
        return round(float(cost), 2) if cost is not None else None
    except Exception as exc:
        logger.warning("Shipping API call failed: %s", exc)
        return None
