from django.urls import path
from . import views

urlpatterns = [
    path("", views.JobListView.as_view(), name="job_list"),
    path("create/", views.JobCreateView.as_view(), name="job_create"),
    path("<uuid:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    # New API endpoints for V8 pipeline
    path("generate_mockup/", views.api_generate_mockup, name="generate_mockup"),
    path("generate_bw/", views.api_generate_bw, name="generate_bw"),
    path("full_pipeline/", views.api_full_pipeline, name="full_pipeline"),
    path("bw_only_pipeline/", views.api_bw_only_pipeline, name="bw_only_pipeline"),
    path("measure/", views.api_measure, name="measure"),
    path("evaluate/", views.api_evaluate, name="evaluate"),
]