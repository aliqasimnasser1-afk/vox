from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from feed.models import Follow, Notification
from feed.notifications import notify, unnotify

from .models import Block, Friendship

User = get_user_model()

NONE, FRIENDS, SELF = "none", "friends", "self"


def between(a, b):
    """The friendship row linking a and b in either direction, or None."""
    return Friendship.objects.filter(
        Q(requester=a, addressee=b) | Q(requester=b, addressee=a), status=Friendship.ACCEPTED
    ).first()


def status_for(viewer, other):
    if viewer.pk == other.pk:
        return SELF
    return FRIENDS if between(viewer, other) else NONE


def are_friends(a, b):
    return status_for(a, b) == FRIENDS


def is_blocked_by(me, other):
    """True when `other` removed me earlier and has not added me back."""
    return Block.objects.filter(blocker=other, blocked=me).exists()


def friends_of(user):
    """Users who are friends with `user`."""
    rows = Friendship.objects.filter(
        Q(requester=user) | Q(addressee=user), status=Friendship.ACCEPTED
    ).select_related("requester__profile", "addressee__profile")
    return [r.addressee if r.requester_id == user.pk else r.requester for r in rows]


def _follow_both(a, b):
    for x, y in ((a, b), (b, a)):
        Follow.objects.get_or_create(follower=x, followee=y)


def add_friend(me, other):
    """Add `other` as a friend, instantly and mutually. Returns 'added', 'friends', 'blocked' or 'self'."""
    if me.pk == other.pk:
        return "self"
    if between(me, other):
        return "friends"
    if is_blocked_by(me, other):
        return "blocked"
    Block.objects.filter(blocker=me, blocked=other).delete()  # adding someone lifts my own block
    # A leftover pending request from the old flow becomes the friendship.
    f = Friendship.objects.filter(
        Q(requester=me, addressee=other) | Q(requester=other, addressee=me)
    ).first()
    if f:
        f.status, f.responded_at = Friendship.ACCEPTED, timezone.now()
        f.save(update_fields=["status", "responded_at"])
    else:
        Friendship.objects.create(requester=me, addressee=other, status=Friendship.ACCEPTED, responded_at=timezone.now())
    _follow_both(me, other)
    unnotify(other, me, Notification.FRIEND_REQUEST)
    notify(other, me, Notification.FRIEND_ADDED)
    return "added"


def remove_friend(me, friendship):
    """Remove a friend. The removed user cannot add me again until I add them."""
    other = friendship.addressee if friendship.requester_id == me.pk else friendship.requester
    friendship.delete()
    Block.objects.get_or_create(blocker=me, blocked=other)
    Follow.objects.filter(Q(follower=me, followee=other) | Q(follower=other, followee=me)).delete()
    unnotify(other, me, Notification.FRIEND_ADDED)
    unnotify(me, other, Notification.FRIEND_ADDED)
    return other
