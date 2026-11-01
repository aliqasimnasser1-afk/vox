import shutil
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def source_path(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"splitter/sources/{instance.user_id}/{uuid.uuid4().hex}{ext}"


class VideoJob(models.Model):
    PENDING, PROCESSING, DONE, FAILED = "pending", "processing", "done", "failed"
    STATUSES = [(PENDING, "في الانتظار"), (PROCESSING, "قيد التقسيم"), (DONE, "جاهز"), (FAILED, "فشل")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_jobs")
    title = models.CharField(max_length=200)
    source = models.FileField(upload_to=source_path)
    segment_seconds = models.PositiveIntegerField()
    duration = models.FloatField(default=0)
    status = models.CharField(max_length=12, choices=STATUSES, default=PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def active(self):
        return self.status in (self.PENDING, self.PROCESSING)

    @property
    def parts_dir(self):
        return Path(settings.MEDIA_ROOT) / "splitter" / "parts" / str(self.pk)

    def delete_files(self):
        if self.source:
            self.source.delete(save=False)
        shutil.rmtree(self.parts_dir, ignore_errors=True)


class VideoPart(models.Model):
    job = models.ForeignKey(VideoJob, on_delete=models.CASCADE, related_name="parts")
    index = models.PositiveIntegerField()
    file = models.FileField(upload_to="splitter/parts/")
    start = models.FloatField()
    duration = models.FloatField()

    class Meta:
        ordering = ["index"]
        constraints = [models.UniqueConstraint(fields=["job", "index"], name="unique_part_index")]
