import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neon_platform.settings.development")

app = Celery("neon_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
