import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

MAX_LEN = 280


def post_image_path(instance, filename):
    return f"posts/images/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def post_video_path(instance, filename):
    return f"posts/videos/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Hashtag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.name}"


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    content = models.CharField(max_length=MAX_LEN, blank=True)
    image = models.ImageField(upload_to=post_image_path, blank=True)
    video = models.FileField(upload_to=post_video_path, blank=True)
    hashtags = models.ManyToManyField(Hashtag, related_name="posts", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}"

    @property
    def has_media(self):
        return bool(self.image or self.video)


@receiver(post_delete, sender=Post)
def delete_post_media(sender, instance, **kwargs):
    for f in (instance.image, instance.video):
        if f:
            f.storage.delete(f.name)


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_like")]


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_bookmark")]


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    followee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "followee"], name="unique_follow"),
            models.CheckConstraint(condition=~models.Q(follower=models.F("followee")), name="no_self_follow"),
        ]


class Notification(models.Model):
    LIKE = "like"
    FOLLOW = "follow"
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPT = "friend_accept"
    KINDS = [(LIKE, "إعجاب"), (FOLLOW, "متابعة"), (FRIEND_REQUEST, "طلب صداقة"), (FRIEND_ACCEPT, "قبول صداقة")]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=20, choices=KINDS)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "is_read"])]
