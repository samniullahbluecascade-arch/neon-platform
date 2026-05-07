from django.contrib import admin
from .models import MeasurementJob


@admin.register(MeasurementJob)
class MeasurementJobAdmin(admin.ModelAdmin):
    list_display  = ["id", "user", "status", "tier_result", "measured_m", "elapsed_s", "created_at"]
    list_filter   = ["status", "tier_result", "physics_ok"]
    search_fields = ["user__email", "id", "celery_task_id"]
    ordering      = ["-created_at"]
    readonly_fields = [
        "id", "celery_task_id", "status", "measured_m", "tier_result", "confidence",
        "tube_width_mm", "px_per_inch", "loc_low_m", "loc_high_m", "area_m",
        "overcount_ratio", "n_paths", "error_pct", "elapsed_s", "reasoning",
        "physics_ok", "input_format", "error_message", "created_at", "finished_at",
    ]
    raw_id_fields = ["user"]
