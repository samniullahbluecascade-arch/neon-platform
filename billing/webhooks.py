"""
Stripe webhook handlers.
dj-stripe routes events to these signal receivers automatically.
"""
import logging
from djstripe import webhooks
from djstripe.models import Subscription

from .models import BillingEvent

logger = logging.getLogger(__name__)


def _get_user_from_subscription(subscription):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    customer_id = subscription.customer.id if hasattr(subscription.customer, "id") else str(subscription.customer)
    return User.objects.filter(stripe_customer_id=customer_id).first()


@webhooks.handler("customer.subscription.updated")
def handle_subscription_updated(event, **kwargs):
    subscription = event.data["object"]
    sub_id  = subscription.get("id", "")
    status  = subscription.get("status", "")
    meta    = subscription.get("metadata", {})
    tier    = meta.get("tier", "")
    user_id = meta.get("user_id", "")

    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = None
    if user_id:
        user = User.objects.filter(pk=user_id).first()

    if user and tier and status == "active":
        old_tier = user.tier
        User.objects.filter(pk=user.pk).update(
            tier=tier,
            stripe_subscription_id=sub_id,
        )
        event_type = (
            BillingEvent.EventType.TIER_UPGRADED
            if tier != "free"
            else BillingEvent.EventType.TIER_DOWNGRADED
        )
        BillingEvent.objects.create(
            user=user,
            event_type=event_type,
            stripe_event_id=event.id,
            payload={"old_tier": old_tier, "new_tier": tier, "subscription_id": sub_id},
        )
        logger.info("User %s tier updated: %s → %s", user.email, old_tier, tier)


@webhooks.handler("customer.subscription.deleted")
def handle_subscription_deleted(event, **kwargs):
    subscription = event.data["object"]
    meta    = subscription.get("metadata", {})
    user_id = meta.get("user_id", "")

    from django.contrib.auth import get_user_model
    User = get_user_model()

    if user_id:
        user = User.objects.filter(pk=user_id).first()
        if user:
            User.objects.filter(pk=user.pk).update(
                tier="free",
                stripe_subscription_id="",
            )
            BillingEvent.objects.create(
                user=user,
                event_type=BillingEvent.EventType.SUBSCRIPTION_CANCELED,
                stripe_event_id=event.id,
                payload={"subscription_id": subscription.get("id")},
            )
            logger.info("User %s downgraded to free (subscription deleted)", user.email)


@webhooks.handler("invoice.payment_succeeded")
def handle_payment_succeeded(event, **kwargs):
    invoice = event.data["object"]
    customer_id = invoice.get("customer", "")

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.filter(stripe_customer_id=customer_id).first()

    BillingEvent.objects.create(
        user=user,
        event_type=BillingEvent.EventType.PAYMENT_SUCCEEDED,
        stripe_event_id=event.id,
        payload={"amount_paid": invoice.get("amount_paid"), "currency": invoice.get("currency")},
    )


@webhooks.handler("invoice.payment_failed")
def handle_payment_failed(event, **kwargs):
    invoice = event.data["object"]
    customer_id = invoice.get("customer", "")

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.filter(stripe_customer_id=customer_id).first()

    BillingEvent.objects.create(
        user=user,
        event_type=BillingEvent.EventType.PAYMENT_FAILED,
        stripe_event_id=event.id,
        payload={"attempt_count": invoice.get("attempt_count")},
    )
    logger.warning("Payment failed for customer %s", customer_id)
