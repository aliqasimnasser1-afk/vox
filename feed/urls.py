from django.urls import path

from . import views

app_name = "feed"

urlpatterns = [
    path("", views.home, name="home"),
    path("post/", views.post_create, name="post_create"),
    path("post/<int:post_id>/like/", views.like_toggle, name="like"),
    path("post/<int:post_id>/delete/", views.post_delete, name="delete"),
    path("u/<str:username>/", views.profile, name="profile"),
    path("u/<str:username>/follow/", views.follow_toggle, name="follow"),
]
