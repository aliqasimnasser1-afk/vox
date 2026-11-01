from django.urls import path

from . import views

app_name = "feed"

urlpatterns = [
    path("", views.home, name="home"),
    path("compose/", views.post_create, name="post_create"),
    path("explore/", views.explore, name="explore"),
    path("search/", views.search, name="search"),
    path("tags/<str:name>/", views.tag_page, name="tag"),
    path("post/<int:post_id>/", views.post_detail, name="post_detail"),
    path("post/<int:post_id>/like/", views.like_toggle, name="like"),
    path("post/<int:post_id>/bookmark/", views.bookmark_toggle, name="bookmark"),
    path("post/<int:post_id>/delete/", views.post_delete, name="delete"),
    path("bookmarks/", views.bookmarks, name="bookmarks"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/badge/", views.notification_badge, name="badge"),
    path("u/<str:username>/", views.profile, name="profile"),
    path("u/<str:username>/follow/", views.follow_toggle, name="follow"),
    path("u/<str:username>/<str:kind>/", views.follow_list, name="follow_list"),
]
