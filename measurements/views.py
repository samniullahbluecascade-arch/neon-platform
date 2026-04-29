from rest_framework import generics, permissions, status
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle

from .models import MeasurementJob, JobStatus
from .serializers import JobCreateSerializer, JobResultSerializer
from .tasks import run_measurement
from .throttles import TierBasedThrottle
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import base64
from v8_generate import generate_mockup, generate_bw
from v8_pipeline import V8Pipeline


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

@csrf_exempt
@permission_classes([permissions.AllowAny])
def api_generate_mockup(request):
    """
    POST /api/generate_mockup
    Expects multipart/form-data with fields:
        - logo (file, required)
        - background (file, optional)
        - additional (text, optional)
    Returns JSON: { "image_b64": "<base64 png>" }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    logo_file = request.FILES.get("logo")
    if not logo_file:
        return JsonResponse({"error": "Missing logo file"}, status=400)

    bg_file = request.FILES.get("background")
    additional = request.POST.get("additional", "")

    try:
        logo_bytes = logo_file.read()
        bg_bytes = bg_file.read() if bg_file else None
        bg_mime = bg_file.content_type if bg_file else None

        mockup_bytes = generate_mockup(
            logo_bytes,
            logo_file.content_type,
            bg_bytes,
            bg_mime,
            additional,
        )
        image_b64 = base64.b64encode(mockup_bytes).decode()
        return JsonResponse({"image_b64": image_b64})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@permission_classes([permissions.AllowAny])
def api_generate_bw(request):
    """
    POST /api/generate_bw
    Expects multipart/form-data with fields:
        - mockup (file, required)
        - additional (text, optional)
    Returns JSON: { "image_b64": "<base64 png>" }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    mockup_file = request.FILES.get("mockup")
    if not mockup_file:
        return JsonResponse({"error": "Missing mockup file"}, status=400)

    additional = request.POST.get("additional", "")

    try:
        mockup_bytes = mockup_file.read()
        bw_bytes = generate_bw(mockup_bytes, mockup_file.content_type, additional)
        image_b64 = base64.b64encode(bw_bytes).decode()
        return JsonResponse({"image_b64": image_b64})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@permission_classes([permissions.AllowAny])
def api_full_pipeline(request):
    """
    POST /api/full_pipeline
    Expects multipart/form-data with fields:
        - logo (file, required)
        - background (file, optional)
        - width_inches (float, required)
        - height_inches (float, optional)
        - additional (text, optional)
        - force_format (text, optional)
        - ground_truth_m (float, optional)
    Returns JSON with the full V8Result fields.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    logo_file = request.FILES.get("logo")
    if not logo_file:
        return JsonResponse({"error": "Missing logo file"}, status=400)

    bg_file = request.FILES.get("background")
    width_inches = request.POST.get("width_inches")
    height_inches = request.POST.get("height_inches")
    additional = request.POST.get("additional", "")
    force_format = request.POST.get("force_format", "")
    gt_m = request.POST.get("ground_truth_m")

    try:
        width_inches = float(width_inches)
        height_inches = float(height_inches) if height_inches else None
        gt_m = float(gt_m) if gt_m else None
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid numeric parameters"}, status=400)

    try:
        logo_bytes = logo_file.read()
        bg_bytes = bg_file.read() if bg_file else None
        bg_mime = bg_file.content_type if bg_file else None

        # Phase 1: Logo → colored mockup
        mockup_bytes = generate_mockup(
            logo_bytes, logo_file.content_type, bg_bytes, bg_mime, additional,
        )
        # Phase 2: Mockup → B&W tube sketch
        bw_bytes = generate_bw(mockup_bytes, "image/png")
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
        return JsonResponse({
            "mockup_b64":  base64.b64encode(mockup_bytes).decode(),
            "bw_b64":      base64.b64encode(bw_bytes).decode(),
            "measurement": _result_to_dict(result),
        })
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
        bw_bytes = generate_bw(mockup_bytes, mockup_file.content_type or "image/png", additional)
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
        return JsonResponse({
            "bw_b64":      base64.b64encode(bw_bytes).decode(),
            "measurement": _result_to_dict(result),
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

    # Reuse the existing serializer logic from JobCreateView
    serializer = JobCreateSerializer(data=request.POST, files=request.FILES)
    if not serializer.is_valid():
        return JsonResponse({"error": serializer.errors}, status=400)

    image_file = serializer.validated_data["image"]
    width_inches = serializer.validated_data["width_inches"]
    height_inches = serializer.validated_data.get("height_inches")
    force_format = serializer.validated_data.get("force_format", "")
    gt_m = serializer.validated_data.get("ground_truth_m")

    try:
        pipeline = V8Pipeline()
        result = pipeline.measure(
            image_file.read(),
            real_width_inches=width_inches,
            real_height_inches=height_inches,
            gt_m=gt_m,
            force_format=force_format or None,
        )
        result_dict = {
            "measured_m": result.measured_m,
            "tier": result.tier,
            "confidence": result.confidence,
            "px_per_inch": result.px_per_inch,
            "px_per_inch_y": result.px_per_inch_y,
            "ar_consistency": result.ar_consistency,
            "tube_width_mm": result.tube_width_mm,
            "gt_m": result.gt_m,
            "error_pct": result.error_pct,
            "n_paths": result.n_paths,
            "physics_ok": result.physics_ok,
            "physics_notes": result.physics_notes,
            "reasoning": result.reasoning,
            "source": result.source,
            "elapsed_s": result.elapsed_s,
            "input_format": result.input_format,
            "loc_low_m": result.loc_low_m,
            "loc_high_m": result.loc_high_m,
            "area_m": result.area_m,
            "overcount_ratio": result.overcount_ratio,
            "tube_cv": getattr(result, "tube_cv", None),
            "tube_width_uncertain": getattr(result, "tube_width_uncertain", None),
            "overlay_b64": result.overlay_b64,
            "ridge_b64": result.ridge_b64,
        }
        return JsonResponse(result_dict)
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
