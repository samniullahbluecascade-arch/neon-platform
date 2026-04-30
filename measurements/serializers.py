from rest_framework import serializers
from .models import MeasurementJob


class JobCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)

    class Meta:
        model  = MeasurementJob
        fields = [
            "image", "width_inches", "height_inches",
            "force_format", "ground_truth_m",
        ]

    def validate_width_inches(self, value):
        if value <= 0:
            raise serializers.ValidationError("width_inches must be positive.")
        return value

    def validate_image(self, value):
        max_bytes = 52_428_800  # 50 MB
        if value.size > max_bytes:
            raise serializers.ValidationError("Image too large (max 50 MB).")
        return value


class JobResultSerializer(serializers.ModelSerializer):
    overlay_url = serializers.SerializerMethodField()
    ridge_url   = serializers.SerializerMethodField()
    mockup_url  = serializers.SerializerMethodField()
    bw_url      = serializers.SerializerMethodField()

    class Meta:
        model  = MeasurementJob
        fields = [
            "id", "status", "celery_task_id",
            "filename", "width_inches", "force_format",
            # result
            "measured_m", "tier_result", "confidence",
            "tube_width_mm", "px_per_inch",
            "loc_low_m", "loc_high_m", "area_m", "overcount_ratio",
            "n_paths", "n_straight_segs", "n_arc_segs", "n_freeform_segs",
            "error_pct", "elapsed_s", "reasoning", "physics_ok", "input_format",
            "estimated_price",
            "error_message",
            "mockup_url", "bw_url", "overlay_url", "ridge_url",
            "created_at", "finished_at",
        ]
        read_only_fields = fields

    def _build_url(self, obj, field):
        image = getattr(obj, field, None)
        if image:
            request = self.context.get("request")
            return request.build_absolute_uri(image.url) if request else image.url
        return None

    def get_overlay_url(self, obj):
        return self._build_url(obj, "overlay_image")

    def get_ridge_url(self, obj):
        return self._build_url(obj, "ridge_image")

    def get_mockup_url(self, obj):
        return self._build_url(obj, "mockup_image")

    def get_bw_url(self, obj):
        return self._build_url(obj, "bw_image")
