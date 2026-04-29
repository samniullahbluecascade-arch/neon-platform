"""
Celery tasks for the measurement pipeline.

The V8 engine lives in the directory pointed to by settings.V8_ENGINE_PATH.
We import it lazily inside the task so Celery workers don't fail if the
path is temporarily unavailable at startup.
"""
import base64
import io
import logging
from datetime import datetime, timezone

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    name="measurements.run_measurement",
)
def run_measurement(self, job_id: str) -> dict:
    """
    Run the V8 LOC measurement pipeline on a MeasurementJob.

    Flow:
      1. Load job from DB
      2. Mark as PROCESSING
      3. Import V8Pipeline (lazy — avoids import errors at worker boot)
      4. Read image bytes from the stored file
      5. Call pipeline.measure_from_bytes()
      6. Persist result fields back to the job
      7. Increment user job counter
    """
    from measurements.models import MeasurementJob, JobStatus

    try:
        job = MeasurementJob.objects.select_related("user").get(pk=job_id)
    except MeasurementJob.DoesNotExist:
        logger.error("run_measurement: job %s not found", job_id)
        return {"error": "job not found"}

    job.status = JobStatus.PROCESSING
    job.celery_task_id = self.request.id or ""
    job.save(update_fields=["status", "celery_task_id"])

    try:
        # ── Lazy import of V8 engine ──────────────────────────────────────────
        import sys
        if settings.V8_ENGINE_PATH not in sys.path:
            sys.path.insert(0, settings.V8_ENGINE_PATH)

        from v8_pipeline import V8Pipeline
        pipeline = V8Pipeline(render_vis=True)

        # ── Read image bytes ──────────────────────────────────────────────────
        job.image.open("rb")
        img_bytes = job.image.read()
        job.image.close()

        # ── Run pipeline ──────────────────────────────────────────────────────
        result = pipeline.measure_from_bytes(
            img_bytes,
            job.width_inches,
            gt_m=job.ground_truth_m,
            filename=job.filename or job.image.name,
            force_format=job.force_format or None,
        )

        # ── Persist result ────────────────────────────────────────────────────
        job.measured_m      = result.measured_m
        job.tier_result     = result.tier
        job.confidence      = result.confidence
        job.tube_width_mm   = result.tube_width_mm
        job.px_per_inch     = result.px_per_inch
        job.loc_low_m       = getattr(result, "loc_low_m", None)
        job.loc_high_m      = getattr(result, "loc_high_m", None)
        job.area_m          = getattr(result, "area_m", None)
        job.overcount_ratio = getattr(result, "overcount_ratio", None)
        job.n_paths         = result.n_paths
        job.n_straight_segs = result.n_straight_segs
        job.n_arc_segs      = result.n_arc_segs
        job.n_freeform_segs = result.n_freeform_segs
        job.error_pct       = result.error_pct
        job.elapsed_s       = result.elapsed_s
        job.reasoning       = result.reasoning or []
        job.physics_ok      = result.physics_ok
        job.input_format    = result.input_format or ""
        job.status          = JobStatus.DONE
        job.finished_at     = datetime.now(timezone.utc)

        # ── Save overlay images ───────────────────────────────────────────────
        if result.overlay_b64:
            overlay_bytes = base64.b64decode(result.overlay_b64)
            job.overlay_image.save(
                f"{job_id}_overlay.png",
                ContentFile(overlay_bytes),
                save=False,
            )
        if result.ridge_b64:
            ridge_bytes = base64.b64decode(result.ridge_b64)
            job.ridge_image.save(
                f"{job_id}_ridge.png",
                ContentFile(ridge_bytes),
                save=False,
            )

        job.save()

        # Usage counting moved to Gemini API call endpoints (views.py)

        logger.info(
            "Job %s done: %.4f m tier=%s elapsed=%.1fs",
            job_id, result.measured_m, result.tier, result.elapsed_s,
        )
        return {"status": "done", "measured_m": result.measured_m, "tier": result.tier}

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        job.save(update_fields=["status", "error_message", "finished_at"])

        # Retry on transient errors (not ValueError/logic errors)
        if not isinstance(exc, (ValueError, TypeError, FileNotFoundError)):
            raise self.retry(exc=exc)

        return {"status": "failed", "error": str(exc)}


@shared_task(name="measurements.reset_monthly_usage")
def reset_monthly_usage():
    """
    Reset all users' monthly job counters.
    Schedule via Celery beat on the 1st of each month.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    updated = User.objects.filter(jobs_used_this_month__gt=0).update(jobs_used_this_month=0)
    logger.info("Monthly reset: cleared counters for %d users", updated)
    return {"reset": updated}
