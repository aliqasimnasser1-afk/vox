from django.urls import path

from . import views

app_name = "social"

urlpatterns = [
    path("friends/", views.friends, name="friends"),
    path("friends/add/", views.friend_add, name="friend_add"),
    path("friends/<int:pk>/<str:action>/", views.friend_respond, name="friend_respond"),
    path("u/<str:username>/friend/", views.friend_request, name="friend_request"),
    path("messages/", views.inbox, name="inbox"),
    path("messages/image/<int:pk>/", views.message_image, name="message_image"),
    path("messages/delete/<int:pk>/", views.message_delete, name="message_delete"),
    path("messages/<str:username>/", views.thread, name="thread"),
    path("messages/<str:username>/send/", views.send, name="send"),
    path("messages/<str:username>/poll/", views.poll, name="poll"),
]
