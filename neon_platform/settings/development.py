from .base import *  # noqa
# Override database configuration for local testing to ensure SQLite works without external dependencies
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# Run Celery tasks inline (no Redis / worker needed in dev)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use console email backend in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relax password validation in dev
AUTH_PASSWORD_VALIDATORS = []

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "measurements": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}
