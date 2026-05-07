from .base import *  # noqa
import sentry_sdk

DEBUG = False

# ── Security headers ──────────────────────────────────────────────────────────
SECURE_HSTS_SECONDS            = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD            = True
SECURE_SSL_REDIRECT            = True
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
SECURE_CONTENT_TYPE_NOSNIFF    = True
SECURE_BROWSER_XSS_FILTER      = True
X_FRAME_OPTIONS                = "DENY"
SECURE_REFERRER_POLICY         = "strict-origin-when-cross-origin"

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND      = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST         = env("EMAIL_HOST")           # noqa: F405
EMAIL_PORT         = env.int("EMAIL_PORT", 587)  # noqa: F405
EMAIL_USE_TLS      = True
EMAIL_HOST_USER    = env("EMAIL_HOST_USER")      # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD") # noqa: F405
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")   # noqa: F405

# ── Sentry error tracking ─────────────────────────────────────────────────────
SENTRY_DSN = env("SENTRY_DSN", default="")      # noqa: F405
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.2,
    )

# ── Static files (WhiteNoise or S3) ──────────────────────────────────────────
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django":       {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "celery":       {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "measurements": {"handlers": ["console"], "level": "INFO",    "propagate": False},
    },
}
