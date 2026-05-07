from django.db import migrations


def bump_free(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.filter(tier_key="free").update(
        jobs_per_month=20,
        description="20 free calculations/month — full pipeline (logo → mockup → LOC → quote).",
    )


def revert_free(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.filter(tier_key="free").update(
        jobs_per_month=10,
        description="Up to 10 measurements/month. Standard accuracy.",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_seed_plans"),
    ]

    operations = [
        migrations.RunPython(bump_free, revert_free),
    ]
