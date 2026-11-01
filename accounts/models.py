from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField("الاسم", max_length=40)
    bio = models.CharField("النبذة", max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"@{self.user.username}"

    @property
    def initial(self):
        return (self.display_name or self.user.username)[:1].upper()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """Every user gets a profile, including ones made from the admin or createsuperuser."""
    if created:
        Profile.objects.create(user=instance, display_name=instance.first_name or instance.username)
