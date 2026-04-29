from rest_framework import serializers
from .models import Plan


class PlanSerializer(serializers.ModelSerializer):
    price_usd = serializers.SerializerMethodField()

    class Meta:
        model  = Plan
        fields = [
            "id", "name", "tier_key", "price_usd", "price_usd_cents",
            "jobs_per_month", "ml_correction", "max_width_px",
            "description", "sort_order",
        ]

    def get_price_usd(self, obj):
        return round(obj.price_usd_cents / 100, 2)
