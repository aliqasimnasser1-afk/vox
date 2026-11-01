from django.db import models


class StoredFile(models.Model):
    """A user-uploaded file kept in the database so it survives restarts on hosts with ephemeral disks."""
    name = models.CharField(max_length=300, unique=True)
    content = models.BinaryField()
    content_type = models.CharField(max_length=100, default="application/octet-stream")
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
