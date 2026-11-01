from django.contrib import admin

from .models import Bookmark, Follow, Hashtag, Like, Notification, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "content", "created_at")
    search_fields = ("content", "author__username")
    list_filter = ("created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "actor", "kind", "is_read", "created_at")
    list_filter = ("kind", "is_read")


admin.site.register(Like)
admin.site.register(Bookmark)
admin.site.register(Follow)

admin.site.register(Hashtag)
