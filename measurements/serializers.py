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
            "error_message",
            "overlay_url", "ridge_url",
            "created_at", "finished_at",
        ]
        read_only_fields = fields

    def get_overlay_url(self, obj):
        if obj.overlay_image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.overlay_image.url) if request else obj.overlay_image.url
        return None

    def get_ridge_url(self, obj):
        if obj.ridge_image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.ridge_image.url) if request else obj.ridge_image.url
        return None
