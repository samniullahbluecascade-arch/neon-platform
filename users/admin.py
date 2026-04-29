from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display   = ["email", "full_name", "tier", "jobs_used_this_month", "is_active", "created_at"]
    list_filter    = ["tier", "is_active", "is_staff", "email_verified"]
    search_fields  = ["email", "full_name", "company", "stripe_customer_id"]
    ordering       = ["-created_at"]
    readonly_fields = ["id", "api_key", "created_at", "updated_at", "stripe_customer_id",
                       "stripe_subscription_id", "jobs_used_this_month"]

    fieldsets = (
        (None,            {"fields": ("id", "email", "password")}),
        ("Profile",       {"fields": ("full_name", "company", "avatar_url")}),
        ("Billing",       {"fields": ("tier", "stripe_customer_id", "stripe_subscription_id",
                                      "billing_cycle_start", "jobs_used_this_month")}),
        ("API",           {"fields": ("api_key",)}),
        ("Permissions",   {"fields": ("is_active", "is_staff", "is_superuser",
                                      "email_verified", "groups", "user_permissions")}),
        ("Timestamps",    {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields":  ("email", "password1", "password2", "tier", "is_staff"),
        }),
    )
