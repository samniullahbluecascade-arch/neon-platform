from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import MeasurementJob, JobStatus
from .serializers import JobCreateSerializer, JobResultSerializer
from .tasks import run_measurement
from .throttles import TierBasedThrottle
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import base64
from v8_generate import (
    generate_mockup,
    generate_bw,
    generate_mockup_with_judge,
    SafetyBlockedError,
)
from v8_pipeline import V8Pipeline
from .shipping import get_shipping_cost


# ─────────────────────────────────────────────────────────────────────────────
#  Tier-based judge-retry budget (matches users.models.Tier values)
#    free       → 0 retries (judge OFF, identical cost to old flow)
#    starter    → 1 retry   (worst-case 2 mockups + 2 judges = 4 gemini calls)
#    business   → 2 retries (worst-case 3 mockups + 3 judges = 6 gemini calls)
#    enterprise → 4 retries (worst-case 5 mockups + 5 judges = 10 gemini calls)
# ─────────────────────────────────────────────────────────────────────────────
TIER_JUDGE_RETRY_BUDGET = {
    "free":       0,
    "starter":    1,
    "business":   2,
    "enterprise": 4,
}


def _retry_budget_for(user) -> int:
    if not user or not getattr(user, "is_authenticated", False):
        return 0
    return TIER_JUDGE_RETRY_BUDGET.get(getattr(user, "tier", "free"), 0)


def _count_gemini_call(request, n=1):
    """Increment user's monthly usage by n (one per Gemini API call)."""
    try:
        auth_result = JWTAuthentication().authenticate(request)
        if auth_result:
            user, _ = auth_result
            for _ in range(n):
                user.increment_job_count()
    except Exception:
        pass  # unauthenticated or invalid token — skip counting


def _compute_pricing(measured_m: float, width_inches: float, bw_bytes: bytes) -> dict:
    """
    Centralised cost calc:
      production = max(25, measured_m * 10)
      shipping   = EpicCraftings cheapest carrier (None if API fails)
      total      = production + (shipping or 0)
    """
    production = round(max(25.0, float(measured_m) * 10.0), 2) if measured_m else None
    shipping = None
    if bw_bytes and width_inches:
        shipping = get_shipping_cost(float(width_inches), bw_bytes)
    total = None
    if production is not None:
        total = round(production + (shipping or 0.0), 2)
    return {
        "estimated_price": production,
        "shipping_cost":   shipping,
        "total_price":     total,
    }


def _result_to_dict(r) -> dict:
    return {
        "measured_m":      round(r.measured_m, 6),
        "tier":            r.tier,
        "confidence":      round(r.confidence, 4),
        "px_per_inch":     round(r.px_per_inch, 2),
        "px_per_inch_y":   round(getattr(r, "px_per_inch_y", 0) or 0, 2),
        "ar_consistency":  round(getattr(r, "ar_consistency", 0) or 0, 4),
        "tube_width_mm":   round(r.tube_width_mm, 2),
        "gt_m":            r.gt_m,
        "error_pct":       round(r.error_pct, 4) if r.error_pct is not None else None,
        "n_paths":         r.n_paths,
        "n_straight_segs": getattr(r, "n_straight_segs", 0),
        "n_arc_segs":      getattr(r, "n_arc_segs", 0),
        "n_freeform_segs": getattr(r, "n_freeform_segs", 0),
        "physics_ok":      r.physics_ok,
        "physics_notes":   r.physics_notes,
        "reasoning":       r.reasoning,
        "source":          r.source,
        "elapsed_s":       round(r.elapsed_s, 3),
        "input_format":    r.input_format,
        "loc_low_m":       round(getattr(r, "loc_low_m", 0) or 0, 4),
        "loc_high_m":      round(getattr(r, "loc_high_m", 0) or 0, 4),
        "area_m":          round(getattr(r, "area_m", 0) or 0, 4),
        "overcount_ratio": round(getattr(r, "overcount_ratio", 1.0) or 1.0, 3),
        "overcount_risk":  round(getattr(r, "overcount_risk", 0) or 0, 3),
        "bias_direction":  getattr(r, "bias_direction", "NEUTRAL"),
        "tube_cv":         round(getattr(r, "tube_cv", 0) or 0, 3),
        "tube_width_uncertain": getattr(r, "tube_width_uncertain", False),
        "overlay_b64":     r.overlay_b64,
        "ridge_b64":       r.ridge_b64,
    }


class JobCreateView(generics.CreateAPIView):
    """
    POST /api/jobs/
    Upload image + dimensions → queues measurement → returns job id.
    """
    serializer_class   = JobCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes   = [TierBasedThrottle]

    def create(self, request, *args, **kwargs):
        user = request.user

        if not user.can_run_job:
            return Response(
                {
                    "error": "Monthly job limit reached.",
                    "tier": user.tier,
                    "jobs_remaining": 0,
                    "upgrade_url": "/api/billing/plans/",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_file = serializer.validated_data["image"]
        job = MeasurementJob.objects.create(
            user          = user,
            image         = image_file,
            filename      = image_file.name,
            width_inches  = serializer.validated_data["width_inches"],
            height_inches = serializer.validated_data.get("height_inches"),
            force_format  = serializer.validated_data.get("force_format", ""),
            ground_truth_m = serializer.validated_data.get("ground_truth_m"),
        )

        # Enqueue the Celery task
        task = run_measurement.delay(str(job.id))
        job.celery_task_id = task.id
        job.save(update_fields=["celery_task_id"])

        return Response(
            {
                "job_id": str(job.id),
                "status": job.status,
                "message": "Job queued. Poll GET /api/jobs/{id}/ for result.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class JobDetailView(generics.RetrieveAPIView):
    """
    GET /api/jobs/{id}/
    Returns full job result (poll until status == done | failed).
    """
    serializer_class   = JobResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MeasurementJob.objects.filter(user=self.request.user)

    def get_object(self):
        return generics.get_object_or_404(
            self.get_queryset(), pk=self.kwargs["pk"]
        )


class JobListView(generics.ListAPIView):
    """
    GET /api/jobs/
    Paginated list of user's jobs, newest first.
    """
    serializer_class   = JobResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = MeasurementJob.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


# -------------------------------------------------------------------------
# New API endpoints required by the Next.js frontend (v8_app.js)
# -------------------------------------------------------------------------

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_generate_mockup(request):
    """
    POST /api/generate_mockup/
    Multipart fields:
        - logo (file, required)
        - background (file, optional)
        - additional (text, optional)
        - uv (text, optional)
        - sign_type   ∈ {"standard","indoor","outdoor","rgb"}      (optional)
        - subtype     (outdoor: pole_sign|monument_sign|...; indoor: living_room|...)
        - outdoor_subtype / indoor_subtype  (accepted aliases of `subtype`)
    Returns JSON: {
        image_b64, subtype, sign_type, attempts, judge_calls, judge_log, final_verdict
    }
    """
    logo_file = request.FILES.get("logo")
    if not logo_file:
        return JsonResponse({"error": "Missing logo file"}, status=400)

    bg_file    = request.FILES.get("background")
    additional = request.POST.get("additional", "")
    uv         = request.POST.get("uv", "")
    sign_type  = request.POST.get("sign_type", "standard")
    subtype    = (request.POST.get("subtype")
                  or request.POST.get("outdoor_subtype")
                  or request.POST.get("indoor_subtype")
                  or None)
    max_retries = _retry_budget_for(request.user)

    try:
        logo_bytes = logo_file.read()
        bg_bytes   = bg_file.read() if bg_file else None
        bg_mime    = bg_file.content_type if bg_file else None

        result = generate_mockup_with_judge(
            logo_bytes=logo_bytes,
            logo_mime=logo_file.content_type,
            bg_bytes=bg_bytes,
            bg_mime=bg_mime,
            additional=additional,
            uv=uv,
            sign_type=sign_type,
            subtype=subtype,
            max_retries=max_retries,
        )
        image_b64 = base64.b64encode(result["mockup_bytes"]).decode()
        _count_gemini_call(request, n=result.get("gemini_calls", 1))
        return JsonResponse({
            "image_b64":     image_b64,
            "sign_type":     sign_type,
            "subtype":       result.get("subtype"),
            "attempts":      result.get("attempts"),
            "judge_calls":   result.get("judge_calls"),
            "judge_log":     result.get("judge_log"),
            "final_verdict": result.get("final_verdict"),
        })
    except SafetyBlockedError as exc:
        return JsonResponse({"error": f"Safety filter blocked generation: {exc}"}, status=422)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_generate_bw(request):
    """
    POST /api/generate_bw/
    Multipart fields:
        - mockup (file, required)
        - additional (text, optional)
        - uv (text, optional)
    Returns JSON: { "image_b64": "<base64 png>" }
    """
    mockup_file = request.FILES.get("mockup")
    if not mockup_file:
        return JsonResponse({"error": "Missing mockup file"}, status=400)

    additional = request.POST.get("additional", "")
    uv         = request.POST.get("uv", "")

    try:
        mockup_bytes = mockup_file.read()
        bw_bytes = generate_bw(mockup_bytes, mockup_file.content_type, additional, uv)
        image_b64 = base64.b64encode(bw_bytes).decode()
        _count_gemini_call(request, n=1)
        return JsonResponse({"image_b64": image_b64})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_full_pipeline(request):
    """
    POST /api/full_pipeline/
    Multipart fields:
        - logo (file, required)
        - background (file, optional)
        - width_inches (float, required)
        - height_inches (float, optional)
        - additional (text, optional, Phase 1)
        - additional_bw (text, optional, Phase 2)
        - uv (text, optional)
        - sign_type   ∈ {"standard","indoor","outdoor","rgb"}      (optional)
        - subtype / outdoor_subtype / indoor_subtype               (optional)
        - force_format (text, optional)
        - ground_truth_m (float, optional)
    Returns JSON: {
        mockup_b64, bw_b64, measurement,
        sign_type, subtype, attempts, judge_calls, judge_log, final_verdict
    }
    """
    logo_file = request.FILES.get("logo")
    if not logo_file:
        return JsonResponse({"error": "Missing logo file"}, status=400)

    bg_file       = request.FILES.get("background")
    width_inches  = request.POST.get("width_inches")
    height_inches = request.POST.get("height_inches")
    additional    = request.POST.get("additional", "")
    additional_bw = request.POST.get("additional_bw", "")
    uv            = request.POST.get("uv", "")
    sign_type     = request.POST.get("sign_type", "standard")
    subtype       = (request.POST.get("subtype")
                     or request.POST.get("outdoor_subtype")
                     or request.POST.get("indoor_subtype")
                     or None)
    force_format  = request.POST.get("force_format", "")
    gt_m          = request.POST.get("ground_truth_m")

    try:
        width_inches  = float(width_inches)
        height_inches = float(height_inches) if height_inches else None
        gt_m          = float(gt_m) if gt_m else None
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid numeric parameters"}, status=400)

    max_retries = _retry_budget_for(request.user)

    try:
        logo_bytes = logo_file.read()
        bg_bytes   = bg_file.read() if bg_file else None
        bg_mime    = bg_file.content_type if bg_file else None

        # Phase 1: Logo → colored mockup (with optional judge-retry loop)
        mockup_result = generate_mockup_with_judge(
            logo_bytes=logo_bytes,
            logo_mime=logo_file.content_type,
            bg_bytes=bg_bytes,
            bg_mime=bg_mime,
            additional=additional,
            uv=uv,
            sign_type=sign_type,
            subtype=subtype,
            max_retries=max_retries,
        )
        mockup_bytes = mockup_result["mockup_bytes"]

        # Phase 2: Mockup → B&W tube sketch
        bw_bytes = generate_bw(mockup_bytes, "image/png", additional_bw or additional, uv)

        # Phase 3: B&W → LOC measurement
        pipeline = V8Pipeline(render_vis=True)
        result = pipeline.measure_from_bytes(
            bw_bytes,
            real_width_inches=width_inches,
            real_height_inches=height_inches,
            gt_m=gt_m,
            filename="studio_bw.png",
            force_format=force_format or "bw",
        )

        # Usage = mockup attempts + judge calls + 1 (B&W).
        gemini_calls_total = int(mockup_result.get("gemini_calls", 1)) + 1
        _count_gemini_call(request, n=gemini_calls_total)

        measurement = _result_to_dict(result)
        measurement.update(_compute_pricing(result.measured_m, width_inches, bw_bytes))
        return JsonResponse({
            "mockup_b64":    base64.b64encode(mockup_bytes).decode(),
            "bw_b64":        base64.b64encode(bw_bytes).decode(),
            "measurement":   measurement,
            "sign_type":     sign_type,
            "subtype":       mockup_result.get("subtype"),
            "attempts":      mockup_result.get("attempts"),
            "judge_calls":   mockup_result.get("judge_calls"),
            "judge_log":     mockup_result.get("judge_log"),
            "final_verdict": mockup_result.get("final_verdict"),
        })
    except SafetyBlockedError as exc:
        return JsonResponse({"error": f"Safety filter blocked generation: {exc}"}, status=422)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@permission_classes([permissions.AllowAny])
def api_bw_only_pipeline(request):
    """
    POST /api/bw_only_pipeline
    Expects multipart/form-data with fields:
        - mockup (file, required)
        - width_inches (float, required)
        - height_inches (float, optional)
        - additional (text, optional)
        - force_format (text, optional)
        - ground_truth_m (float, optional)
    Returns JSON with the V8Result fields.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    mockup_file = request.FILES.get("mockup")
    if not mockup_file:
        return JsonResponse({"error": "Missing mockup file"}, status=400)

    width_inches = request.POST.get("width_inches")
    height_inches = request.POST.get("height_inches")
    additional = request.POST.get("additional", "")
    uv         = request.POST.get("uv", "")
    force_format = request.POST.get("force_format", "")
    gt_m = request.POST.get("ground_truth_m")

    try:
        width_inches = float(width_inches)
        height_inches = float(height_inches) if height_inches else None
        gt_m = float(gt_m) if gt_m else None
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid numeric parameters"}, status=400)

    try:
        mockup_bytes = mockup_file.read()
        # Phase 2: Mockup → B&W tube sketch
        bw_bytes = generate_bw(mockup_bytes, mockup_file.content_type or "image/png", additional, uv)
        # Phase 3: B&W → LOC measurement
        pipeline = V8Pipeline(render_vis=True)
        result = pipeline.measure_from_bytes(
            bw_bytes,
            real_width_inches=width_inches,
            real_height_inches=height_inches,
            gt_m=gt_m,
            filename="studio_bw.png",
            force_format=force_format or "bw",
        )
        _count_gemini_call(request, n=1)  # B&W = 1 Gemini call
        measurement = _result_to_dict(result)
        measurement.update(_compute_pricing(result.measured_m, width_inches, bw_bytes))
        return JsonResponse({
            "bw_b64":      base64.b64encode(bw_bytes).decode(),
            "measurement": measurement,
        })
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@permission_classes([permissions.AllowAny])
def api_measure(request):
    """
    POST /measure
    Legacy endpoint used by the original Flask app.
    Accepts the same fields as JobCreateView and returns the measurement result
    directly (no job polling).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # Reuse the existing serializer logic from JobCreateView. DRF serializers
    # take a single `data=` kwarg — merge POST + FILES into one mutable
    # QueryDict so the ImageField sees the upload.
    merged = request.POST.copy()
    for k, v in request.FILES.items():
        merged[k] = v
    serializer = JobCreateSerializer(data=merged)
    if not serializer.is_valid():
        return JsonResponse({"error": serializer.errors}, status=400)

    image_file = serializer.validated_data["image"]
    width_inches = serializer.validated_data["width_inches"]
    height_inches = serializer.validated_data.get("height_inches")
    force_format = serializer.validated_data.get("force_format", "")
    gt_m = serializer.validated_data.get("ground_truth_m")

    try:
        bw_bytes = image_file.read()
        pipeline = V8Pipeline(render_vis=True)
        result = pipeline.measure_from_bytes(
            bw_bytes,
            real_width_inches=width_inches,
            real_height_inches=height_inches,
            gt_m=gt_m,
            filename="studio_measure.png",
            force_format=force_format or None,
        )
        # Reuse the canonical V8Result → dict converter so every field the
        # Studio Results card expects (n_*_segs, bias_direction, etc.) lands.
        out = _result_to_dict(result)
        out.update(_compute_pricing(result.measured_m, width_inches, bw_bytes))
        return JsonResponse(out)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@permission_classes([permissions.AllowAny])
def api_evaluate(request):
    """
    GET /evaluate
    Runs batch evaluation over the Ground_Truth folder (same behaviour as the
    original Flask endpoint). Returns JSON with the evaluation summary.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        from v8_pipeline import batch_evaluate, TIER_THRESHOLDS

        eval_result = batch_evaluate()
        return JsonResponse(eval_result, safe=False)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)
