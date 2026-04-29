from django.contrib import admin
from .models import Plan, BillingEvent


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display  = ["name", "tier_key", "price_usd_cents", "jobs_per_month", "is_active", "sort_order"]
    list_editable = ["is_active", "sort_order"]
    ordering      = ["sort_order"]


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display  = ["event_type", "user", "stripe_event_id", "created_at"]
    list_filter   = ["event_type"]
    search_fields = ["user__email", "stripe_event_id"]
    ordering      = ["-created_at"]
    readonly_fields = ["event_type", "user", "stripe_event_id", "payload", "created_at"]
