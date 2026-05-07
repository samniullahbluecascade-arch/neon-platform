import stripe
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Plan, BillingEvent
from .serializers import PlanSerializer


class PlanListView(generics.ListAPIView):
    """
    GET /api/billing/plans/
    Returns all active plans. Public endpoint — no auth required.
    """
    serializer_class   = PlanSerializer
    permission_classes = [permissions.AllowAny]
    queryset           = Plan.objects.filter(is_active=True)


class CreateCheckoutSessionView(APIView):
    """
    POST /api/billing/checkout/
    Body: { "plan_id": <int> }
    Returns a Stripe Checkout session URL. Frontend redirects the user there.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        try:
            plan = Plan.objects.get(pk=plan_id, is_active=True)
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        if not plan.stripe_price_id:
            return Response({"error": "Plan not yet available for purchase."}, status=400)

        stripe.api_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if settings.STRIPE_LIVE_MODE
            else settings.STRIPE_TEST_SECRET_KEY
        )

        user = request.user
        # Create or reuse Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.pk)},
            )
            from django.contrib.auth import get_user_model
            get_user_model().objects.filter(pk=user.pk).update(
                stripe_customer_id=customer.id
            )
            customer_id = customer.id
        else:
            customer_id = user.stripe_customer_id

        success_url = request.data.get("success_url", "http://localhost:3000/dashboard?upgraded=1")
        cancel_url  = request.data.get("cancel_url",  "http://localhost:3000/pricing")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user.pk), "plan_id": str(plan.pk), "tier": plan.tier_key},
        )

        return Response({"checkout_url": session.url, "session_id": session.id})


class CancelSubscriptionView(APIView):
    """
    POST /api/billing/cancel/
    Cancels the current Stripe subscription at period end.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.stripe_subscription_id:
            return Response({"error": "No active subscription."}, status=400)

        stripe.api_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if settings.STRIPE_LIVE_MODE
            else settings.STRIPE_TEST_SECRET_KEY
        )

        sub = stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=True,
        )

        BillingEvent.objects.create(
            user=user,
            event_type=BillingEvent.EventType.SUBSCRIPTION_CANCELED,
            payload={"subscription_id": sub.id, "cancel_at": sub.cancel_at},
        )

        return Response({
            "message": "Subscription will cancel at end of billing period.",
            "cancel_at": sub.cancel_at,
        })


class BillingPortalView(APIView):
    """
    POST /api/billing/portal/
    Returns Stripe Customer Portal URL for self-serve billing management.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.stripe_customer_id:
            return Response({"error": "No billing account found."}, status=400)

        stripe.api_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if settings.STRIPE_LIVE_MODE
            else settings.STRIPE_TEST_SECRET_KEY
        )

        return_url = request.data.get("return_url", "http://localhost:3000/dashboard")
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=return_url,
        )
        return Response({"portal_url": session.url})
