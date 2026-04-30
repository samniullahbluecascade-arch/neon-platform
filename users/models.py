import uuid
import secrets
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class Tier(models.TextChoices):
    FREE       = "free",       "Free"
    STARTER    = "starter",    "Starter"
    BUSINESS   = "business",   "Business"
    ENTERPRISE = "enterprise", "Enterprise"


TIER_LIMITS = {
    Tier.FREE:       {"jobs_per_month": 20,   "max_width_px": 2000,  "ml_correction": False},
    Tier.STARTER:    {"jobs_per_month": 200,  "max_width_px": 4000,  "ml_correction": False},
    Tier.BUSINESS:   {"jobs_per_month": 600,  "max_width_px": 8000,  "ml_correction": True},
    Tier.ENTERPRISE: {"jobs_per_month": 1500, "max_width_px": 99999, "ml_correction": True},
}


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("tier", Tier.ENTERPRISE)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True)

    full_name  = models.CharField(max_length=255, blank=True)
    company    = models.CharField(max_length=255, blank=True)
    avatar_url = models.URLField(blank=True)

    tier                   = models.CharField(max_length=20, choices=Tier.choices, default=Tier.FREE)
    stripe_customer_id     = models.CharField(max_length=64, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=64, blank=True)
    billing_cycle_start    = models.DateField(null=True, blank=True)
    jobs_used_this_month   = models.PositiveIntegerField(default=0)

    api_key = models.CharField(max_length=64, unique=True, db_index=True, blank=True)

    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tier"]),
            models.Index(fields=["stripe_customer_id"]),
        ]

    def __str__(self):
        return f"{self.email} [{self.tier}]"

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(40)
        super().save(*args, **kwargs)

    @property
    def tier_limits(self) -> dict:
        return TIER_LIMITS[self.tier]

    @property
    def jobs_remaining(self) -> int:
        return max(0, self.tier_limits["jobs_per_month"] - self.jobs_used_this_month)

    @property
    def can_run_job(self) -> bool:
        return self.jobs_remaining > 0

    @property
    def ml_correction_enabled(self) -> bool:
        return self.tier_limits["ml_correction"]

    def increment_job_count(self):
        User.objects.filter(pk=self.pk).update(
            jobs_used_this_month=models.F("jobs_used_this_month") + 1
        )

    def reset_monthly_usage(self):
        User.objects.filter(pk=self.pk).update(jobs_used_this_month=0)

    def rotate_api_key(self) -> str:
        new_key = secrets.token_urlsafe(40)
        User.objects.filter(pk=self.pk).update(api_key=new_key)
        self.api_key = new_key
        return new_key
