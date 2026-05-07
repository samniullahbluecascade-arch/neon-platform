from django.db import migrations


PLANS = [
    {
        "name": "Free",
        "tier_key": "free",
        "stripe_price_id": "",
        "price_usd_cents": 0,
        "jobs_per_month": 10,
        "ml_correction": False,
        "max_width_px": 2000,
        "is_active": True,
        "description": "Up to 10 measurements/month. Standard accuracy.",
        "sort_order": 0,
    },
    {
        "name": "Pro",
        "tier_key": "pro",
        "stripe_price_id": "",
        "price_usd_cents": 4900,
        "jobs_per_month": 500,
        "ml_correction": True,
        "max_width_px": 8000,
        "is_active": True,
        "description": "500 measurements/month + ML correction + high-res.",
        "sort_order": 1,
    },
    {
        "name": "Enterprise",
        "tier_key": "enterprise",
        "stripe_price_id": "",
        "price_usd_cents": 49900,
        "jobs_per_month": 99999,
        "ml_correction": True,
        "max_width_px": 99999,
        "is_active": True,
        "description": "Unlimited measurements, priority queue, SLA.",
        "sort_order": 2,
    },
]


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    for p in PLANS:
        Plan.objects.update_or_create(tier_key=p["tier_key"], defaults=p)


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.filter(tier_key__in=[p["tier_key"] for p in PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
