from django.urls import path

from . import chunked, views

app_name = "splitter"

urlpatterns = [
    path("splitter/", views.index, name="index"),
    path("splitter/upload/init/", chunked.init, name="chunk_init"),
    path("splitter/upload/chunk/", chunked.chunk, name="chunk"),
    path("splitter/upload/finish/", chunked.finish, name="chunk_finish"),
    path("splitter/upload/abort/", chunked.abort, name="chunk_abort"),
    path("splitter/<int:job_id>/", views.detail, name="detail"),
    path("splitter/<int:job_id>/status/", views.status, name="status"),
    path("splitter/<int:job_id>/retry/", views.retry, name="retry"),
    path("splitter/<int:job_id>/delete/", views.delete, name="delete"),
    path("splitter/<int:job_id>/zip/", views.download_zip, name="zip"),
    path("splitter/<int:job_id>/part/<int:index>/", views.part_file, name="part"),
]
