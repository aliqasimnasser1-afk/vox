from django.urls import path

from . import views

app_name = "splitter"

urlpatterns = [
    path("splitter/", views.index, name="index"),
    path("splitter/<int:job_id>/", views.detail, name="detail"),
    path("splitter/<int:job_id>/status/", views.status, name="status"),
    path("splitter/<int:job_id>/retry/", views.retry, name="retry"),
    path("splitter/<int:job_id>/delete/", views.delete, name="delete"),
    path("splitter/<int:job_id>/zip/", views.download_zip, name="zip"),
]
