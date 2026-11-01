from .models import Message


def counts(request):
    """Sidebar badge: unread private messages."""
    user = request.user
    if not user.is_authenticated:
        return {}
    return {"unread_messages_count": Message.objects.filter(recipient=user, read_at__isnull=True).count()}
