from django.contrib import admin

from .models import Friendship, Message

admin.site.register(Friendship)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "recipient", "created_at", "read_at")
