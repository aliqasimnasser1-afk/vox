from django.contrib.auth import get_user_model
from django.db.models import Count

from .hashtags import trending
from .models import Notification

User = get_user_model()


def sidebar(request):
    """Unread count for the nav badge and a few accounts to follow for the right rail."""
    user = request.user
    if not user.is_authenticated:
        return {}
    suggestions = (
        User.objects.exclude(pk=user.pk)
        .exclude(followers__follower=user)
        .select_related("profile")
        .annotate(follower_total=Count("followers"))
        .order_by("-follower_total", "-date_joined")[:4]
    )
    return {
        "unread_count": Notification.objects.filter(recipient=user, is_read=False).count(),
        "suggestions": suggestions,
        "trending": trending(6),
    }
