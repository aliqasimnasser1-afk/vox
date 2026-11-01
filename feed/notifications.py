from .models import Notification


def notify(recipient, actor, kind, post=None):
    """Create a notification once per (recipient, actor, kind, post). Never notify yourself."""
    if recipient.pk == actor.pk:
        return
    Notification.objects.get_or_create(recipient=recipient, actor=actor, kind=kind, post=post)


def unnotify(recipient, actor, kind, post=None):
    """Undo a notification when the like or follow is withdrawn."""
    Notification.objects.filter(recipient=recipient, actor=actor, kind=kind, post=post).delete()
