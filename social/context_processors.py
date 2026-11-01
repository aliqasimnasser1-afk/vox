from .models import Friendship, Message


def counts(request):
    """Badges for the sidebar: pending friend requests and unread messages."""
    user = request.user
    if not user.is_authenticated:
        return {}
    return {
        "friend_requests_count": Friendship.objects.filter(addressee=user, status=Friendship.PENDING).count(),
        "unread_messages_count": Message.objects.filter(recipient=user, read_at__isnull=True).count(),
    }
