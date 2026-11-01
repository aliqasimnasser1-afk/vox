from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .models import Friendship, Message

User = get_user_model()
MAX_BODY = 1000


def _safe_next(request, default):
    nxt = request.POST.get("next", "")
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else default


@login_required
def friends(request):
    tab = request.GET.get("tab", "friends")
    me = request.user
    received = Friendship.objects.filter(addressee=me, status=Friendship.PENDING).select_related("requester__profile")
    sent = Friendship.objects.filter(requester=me, status=Friendship.PENDING).select_related("addressee__profile")
    return render(request, "social/friends.html", {
        "tab": tab if tab in ("friends", "requests", "add") else "friends",
        "friends": services.friends_of(me),
        "received": received,
        "sent": sent,
        "nav": "friends",
    })


@login_required
@require_POST
def friend_add(request):
    """Add a friend by typing their username."""
    name = request.POST.get("username", "").strip().lstrip("@").lower()
    other = User.objects.filter(username__iexact=name).first() if name else None
    if not other:
        messages.error(request, "لا يوجد مستخدم بهذا الاسم.")
        return redirect("/friends/?tab=add")
    return _do_request(request, other, redirect_to="/friends/?tab=requests")


@login_required
@require_POST
def friend_request(request, username):
    other = get_object_or_404(User, username=username)
    return _do_request(request, other, redirect_to=_safe_next(request, f"/u/{other.username}/"))


def _do_request(request, other, redirect_to):
    result = services.send_request(request.user, other)
    text = {
        "sent": f"تم إرسال طلب الصداقة إلى @{other.username}.",
        "accepted": f"أنتما الآن صديقان مع @{other.username}.",
        "friends": "أنتما صديقان بالفعل.",
        "exists": "أرسلتَ طلباً مسبقاً وهو بانتظار الرد.",
        "self": "لا يمكنك إضافة نفسك.",
    }[result]
    (messages.error if result == "self" else messages.success)(request, text)
    return redirect(redirect_to)


@login_required
@require_POST
def friend_respond(request, pk, action):
    f = get_object_or_404(Friendship, pk=pk)
    me = request.user
    if action == "accept" and f.addressee_id == me.pk and f.status == Friendship.PENDING:
        services.accept(f)
        messages.success(request, f"أصبحتَ صديقاً لـ @{f.requester.username}.")
    elif action in ("decline", "cancel", "unfriend") and me.pk in (f.requester_id, f.addressee_id):
        services.remove(f)
        messages.success(request, "تم.")
    else:
        raise Http404
    return redirect(_safe_next(request, "/friends/?tab=requests"))


# ───────── private messages ─────────

def _conversations(me):
    """Friends with their last message and unread count, most recent conversation first."""
    friends = {u.pk: u for u in services.friends_of(me)}
    last, unread = {}, {}
    for m in Message.objects.filter(Q(sender=me) | Q(recipient=me)).order_by("-id")[:500]:
        other_id = m.recipient_id if m.sender_id == me.pk else m.sender_id
        last.setdefault(other_id, m)
        if m.recipient_id == me.pk and m.read_at is None:
            unread[other_id] = unread.get(other_id, 0) + 1
    rows = [{"user": u, "last": last.get(pk), "unread": unread.get(pk, 0)} for pk, u in friends.items()]
    rows.sort(key=lambda r: r["last"].id if r["last"] else 0, reverse=True)
    return rows


@login_required
def inbox(request):
    return render(request, "social/inbox.html", {"rows": _conversations(request.user), "nav": "messages"})


def _friend_or_404(request, username):
    other = get_object_or_404(User.objects.select_related("profile"), username=username)
    if not services.are_friends(request.user, other):
        raise Http404
    return other


@login_required
def thread(request, username):
    other = _friend_or_404(request, username)
    me = request.user
    Message.objects.filter(sender=other, recipient=me, read_at__isnull=True).update(read_at=timezone.now())
    msgs = list(Message.objects.filter(Q(sender=me, recipient=other) | Q(sender=other, recipient=me)).order_by("-id")[:100])[::-1]
    return render(request, "social/thread.html", {
        "other": other, "msgs": msgs, "last_id": msgs[-1].id if msgs else 0, "nav": "messages",
    })


@login_required
@require_POST
def send(request, username):
    other = _friend_or_404(request, username)
    body = request.POST.get("body", "").strip()[:MAX_BODY]
    if not body:
        return HttpResponse(status=204) if request.headers.get("HX-Request") else redirect("social:thread", username=username)
    m = Message.objects.create(sender=request.user, recipient=other, body=body)
    if request.headers.get("HX-Request"):
        return render(request, "social/_bubble.html", {"m": m})
    return redirect("social:thread", username=username)


@login_required
def poll(request, username):
    """New messages from the other person since `after`, followed by a fresh poller element."""
    other = _friend_or_404(request, username)
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    new = list(Message.objects.filter(sender=other, recipient=request.user, id__gt=after).order_by("id"))
    if new:
        Message.objects.filter(pk__in=[m.pk for m in new]).update(read_at=timezone.now())
        after = new[-1].id
    return render(request, "social/_poll.html", {"new": new, "other": other, "after": after})
