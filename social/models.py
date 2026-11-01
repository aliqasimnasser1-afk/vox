from django.conf import settings
from django.db import models
from django.db.models import Q


class Friendship(models.Model):
    """A friend request (pending) that becomes a friendship (accepted)."""
    PENDING, ACCEPTED = "pending", "accepted"
    STATUSES = [(PENDING, "قيد الانتظار"), (ACCEPTED, "أصدقاء")]

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_sent")
    addressee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=10, choices=STATUSES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["requester", "addressee"], name="unique_friend_request"),
            models.CheckConstraint(condition=~Q(requester=models.F("addressee")), name="no_self_friend"),
        ]


class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_sent")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages_received")
    body = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["recipient", "read_at"]),
            models.Index(fields=["sender", "recipient", "id"]),
        ]
