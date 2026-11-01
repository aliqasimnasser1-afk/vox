from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from feed.models import Notification
from feed.notifications import notify, unnotify

from .models import Friendship

User = get_user_model()

NONE, FRIENDS, SENT, RECEIVED, SELF = "none", "friends", "sent", "received", "self"


def between(a, b):
    """The friendship row linking a and b in either direction, or None."""
    return Friendship.objects.filter(
        Q(requester=a, addressee=b) | Q(requester=b, addressee=a)
    ).first()


def status_for(viewer, other):
    if viewer.pk == other.pk:
        return SELF
    f = between(viewer, other)
    if not f:
        return NONE
    if f.status == Friendship.ACCEPTED:
        return FRIENDS
    return SENT if f.requester_id == viewer.pk else RECEIVED


def are_friends(a, b):
    return status_for(a, b) == FRIENDS


def friends_of(user):
    """Users who are friends with `user`."""
    rows = Friendship.objects.filter(
        Q(requester=user) | Q(addressee=user), status=Friendship.ACCEPTED
    ).select_related("requester__profile", "addressee__profile")
    return [r.addressee if r.requester_id == user.pk else r.requester for r in rows]


def send_request(me, other):
    """Returns 'sent', 'accepted' (they had already asked me), 'friends', 'exists' or 'self'."""
    if me.pk == other.pk:
        return "self"
    f = between(me, other)
    if f:
        if f.status == Friendship.ACCEPTED:
            return "friends"
        if f.addressee_id == me.pk:
            accept(f)
            return "accepted"
        return "exists"
    Friendship.objects.create(requester=me, addressee=other)
    notify(other, me, Notification.FRIEND_REQUEST)
    return "sent"


def accept(friendship):
    friendship.status = Friendship.ACCEPTED
    friendship.responded_at = timezone.now()
    friendship.save(update_fields=["status", "responded_at"])
    unnotify(friendship.addressee, friendship.requester, Notification.FRIEND_REQUEST)
    notify(friendship.requester, friendship.addressee, Notification.FRIEND_ACCEPT)


def remove(friendship):
    """Decline, cancel or unfriend: all just delete the row (and the pending notification)."""
    unnotify(friendship.addressee, friendship.requester, Notification.FRIEND_REQUEST)
    friendship.delete()
