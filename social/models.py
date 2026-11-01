import re
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver

EMOJI_ONLY = re.compile(r"^[\U0001F000-\U0001FAFF←-⇿⌀-⏿①-⓿■-➿⤀-⥿⬀-⯿️‍⃣\s]{1,16}$")


class Friendship(models.Model):
    """Adding a friend is instant and mutual. `pending` only exists for rows created by the old request flow."""
    PENDING, ACCEPTED = "pending", "accepted"
    STATUSES = [(PENDING, "قيد الانتظار"), (ACCEPTED, "أصدقاء")]

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_sent")
    addressee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=10, choices=STATUSES, default=ACCEPTED)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["requester", "addressee"], name="unique_friend_request"),
            models.CheckConstraint(condition=~Q(requester=models.F("addressee")), name="no_self_friend"),
        ]


class Block(models.Model):
    """Removing a friend blocks that user from adding you again, until you add them yourself."""
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block")]


def message_image_path(instance, filename):
    return f"messages/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Message(models.Model):
    TEXT, STICKER, IMAGE = "text", "sticker", "image"
    KINDS = [(TEXT, "نص"), (STICKER, "ملصق"), (IMAGE, "صورة")]

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_sent")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_received")
    kind = models.CharField(max_length=8, choices=KINDS, default=TEXT)
    body = models.CharField(max_length=1000, blank=True)  # text, caption (image) or the sticker itself
    image = models.ImageField(upload_to=message_image_path, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["recipient", "read_at"]),
            models.Index(fields=["sender", "recipient", "id"]),
        ]

    @property
    def emoji_only(self):
        return self.kind == self.TEXT and bool(EMOJI_ONLY.match(self.body)) and len(self.body.strip()) <= 12

    @property
    def preview(self):
        """Short text for the inbox list."""
        if self.kind == self.STICKER:
            return f"ملصق {self.body}"
        if self.kind == self.IMAGE:
            return "صورة" + (f": {self.body}" if self.body else "")
        return self.body


@receiver(post_delete, sender=Message)
def delete_message_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.storage.delete(instance.image.name)
