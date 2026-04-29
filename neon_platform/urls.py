from django.contrib import admin
from django.urls import path, include
from measurements import views as measurement_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/",        admin.site.urls),
    path("api/auth/",     include("users.urls")),
    path("api/jobs/",     include("measurements.urls")),
    # New V8 pipeline API endpoints
    path("api/generate_mockup/",   measurement_views.api_generate_mockup,   name="generate_mockup"),
    path("api/generate_bw/",       measurement_views.api_generate_bw,       name="generate_bw"),
    path("api/full_pipeline/",     measurement_views.api_full_pipeline,     name="full_pipeline"),
    path("api/bw_only_pipeline/", measurement_views.api_bw_only_pipeline, name="bw_only_pipeline"),
    path("api/measure/",           measurement_views.api_measure,           name="measure"),
    path("api/evaluate/",          measurement_views.api_evaluate,          name="evaluate"),
    path("api/billing/",  include("billing.urls")),
    path("api/stripe/",   include("djstripe.urls", namespace="djstripe")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
