"""
Staging / demo settings for Render deployment.
Like development but with proper security for public access.
"""
from .base import *  # noqa

DEBUG = False

# Allow Render domain + custom
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])  # noqa: F405

# CORS — allow Vercel frontend
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)  # noqa: F405
CORS_ALLOW_CREDENTIALS = True

# Celery eager — no Redis needed on free tier
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Console email
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relaxed passwords for demo
AUTH_PASSWORD_VALIDATORS = []

# WhiteNoise for static files
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# SQLite (ephemeral on Render — fine for demo)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# No SSL redirect for free tier (no custom domain)
SECURE_SSL_REDIRECT = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
