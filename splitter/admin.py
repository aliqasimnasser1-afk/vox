from django.contrib import admin

from .models import VideoJob, VideoPart


class PartInline(admin.TabularInline):
    model = VideoPart
    extra = 0


@admin.register(VideoJob)
class VideoJobAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "segment_seconds", "status", "created_at")
    list_filter = ("status",)
    inlines = [PartInline]
