"""
Thin billing models.
Heavy lifting (subscription state, invoices, webhooks) is handled by dj-stripe.
We only store what we need for fast business-logic queries.
"""
from django.db import models
from django.conf import settings


class Plan(models.Model):
    """
    Static plan definitions — editable from admin without code changes.
    Link to a Stripe Price ID for dj-stripe to sync.
    """
    name             = models.CharField(max_length=50, unique=True)   # "Pro", "Enterprise"
    tier_key         = models.CharField(max_length=20, unique=True)    # "pro", "enterprise"
    stripe_price_id  = models.CharField(max_length=64, blank=True)     # price_xxxx
    price_usd_cents  = models.PositiveIntegerField(default=0)          # monthly price in cents
    jobs_per_month   = models.PositiveIntegerField(default=0)
    ml_correction    = models.BooleanField(default=False)
    max_width_px     = models.PositiveIntegerField(default=2000)
    is_active        = models.BooleanField(default=True)
    description      = models.TextField(blank=True)
    sort_order       = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} (${self.price_usd_cents / 100:.2f}/mo)"


class BillingEvent(models.Model):
    """
    Append-only audit log for billing-related events.
    Stripe webhooks write here via signals.
    """
    class EventType(models.TextChoices):
        SUBSCRIPTION_CREATED  = "subscription.created"
        SUBSCRIPTION_UPDATED  = "subscription.updated"
        SUBSCRIPTION_CANCELED = "subscription.canceled"
        PAYMENT_SUCCEEDED     = "payment.succeeded"
        PAYMENT_FAILED        = "payment.failed"
        TIER_UPGRADED         = "tier.upgraded"
        TIER_DOWNGRADED       = "tier.downgraded"

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="billing_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    stripe_event_id = models.CharField(max_length=64, blank=True, db_index=True)
    payload    = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} — {self.user} @ {self.created_at:%Y-%m-%d}"
