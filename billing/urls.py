from django.urls import path
from . import views

urlpatterns = [
    path("plans/",    views.PlanListView.as_view(),            name="plan_list"),
    path("checkout/", views.CreateCheckoutSessionView.as_view(), name="create_checkout"),
    path("cancel/",   views.CancelSubscriptionView.as_view(),   name="cancel_subscription"),
    path("portal/",   views.BillingPortalView.as_view(),        name="billing_portal"),
]
