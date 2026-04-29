import uuid
from django.db import models
from django.conf import settings


class JobStatus(models.TextChoices):
    PENDING    = "pending",    "Pending"
    PROCESSING = "processing", "Processing"
    DONE       = "done",       "Done"
    FAILED     = "failed",     "Failed"


class MeasurementJob(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jobs",
    )

    # ── Input ─────────────────────────────────────────────────────────────────
    image      = models.ImageField(upload_to="uploads/%Y/%m/%d/")
    filename   = models.CharField(max_length=255, blank=True)
    width_inches  = models.FloatField()
    height_inches = models.FloatField(null=True, blank=True)
    force_format  = models.CharField(max_length=20, blank=True)  # bw / transparent / colored
    ground_truth_m = models.FloatField(null=True, blank=True)

    # ── Job state ─────────────────────────────────────────────────────────────
    status     = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING)
    celery_task_id = models.CharField(max_length=64, blank=True, db_index=True)

    # ── Result (populated when done) ──────────────────────────────────────────
    measured_m       = models.FloatField(null=True, blank=True)
    tier_result      = models.CharField(max_length=20, blank=True)  # GLASS_CUT / QUOTE / etc.
    confidence       = models.FloatField(null=True, blank=True)
    tube_width_mm    = models.FloatField(null=True, blank=True)
    px_per_inch      = models.FloatField(null=True, blank=True)
    loc_low_m        = models.FloatField(null=True, blank=True)
    loc_high_m       = models.FloatField(null=True, blank=True)
    area_m           = models.FloatField(null=True, blank=True)
    overcount_ratio  = models.FloatField(null=True, blank=True)
    n_paths          = models.IntegerField(null=True, blank=True)
    n_straight_segs  = models.IntegerField(null=True, blank=True)
    n_arc_segs       = models.IntegerField(null=True, blank=True)
    n_freeform_segs  = models.IntegerField(null=True, blank=True)
    error_pct        = models.FloatField(null=True, blank=True)
    elapsed_s        = models.FloatField(null=True, blank=True)
    reasoning        = models.JSONField(default=list, blank=True)
    physics_ok       = models.BooleanField(null=True)
    input_format     = models.CharField(max_length=30, blank=True)

    # Visualisation overlays stored as separate media files
    overlay_image = models.ImageField(upload_to="overlays/%Y/%m/%d/", null=True, blank=True)
    ridge_image   = models.ImageField(upload_to="ridges/%Y/%m/%d/",   null=True, blank=True)

    error_message = models.TextField(blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Job {self.id} [{self.status}] — {self.user.email}"
