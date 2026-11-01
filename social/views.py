from datetime import timedelta
from itertools import groupby

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from feed.media import classify

from . import services
from .models import EMOJI_ONLY, Friendship, Message

User = get_user_model()
MAX_BODY = 1000


def _safe_next(request, default):
    nxt = request.POST.get("next", "")
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else default


# ───────── friends ─────────

@login_required
def friends(request):
    tab = "add" if request.GET.get("tab") == "add" else "friends"
    return render(request, "social/friends.html", {
        "tab": tab, "friends": services.friends_of(request.user), "nav": "friends",
    })


def _do_add(request, other, redirect_to):
    result = services.add_friend(request.user, other)
    text = {
        "added": f"أضفتَ @{other.username} إلى أصدقائك.",
        "friends": "أنتما صديقان بالفعل.",
        "blocked": "لا يمكنك إضافة هذا المستخدم.",
        "self": "لا يمكنك إضافة نفسك.",
    }[result]
    (messages.success if result == "added" else messages.error)(request, text)
    return redirect(redirect_to)


@login_required
@require_POST
def friend_add(request):
    """Add a friend by typing their username. One step: they become your friend immediately."""
    name = request.POST.get("username", "").strip().lstrip("@").lower()
    other = User.objects.filter(username__iexact=name).first() if name else None
    if not other:
        messages.error(request, "لا يوجد مستخدم بهذا الاسم.")
        return redirect("/friends/?tab=add")
    return _do_add(request, other, "/friends/")


@login_required
@require_POST
def friend_request(request, username):
    other = get_object_or_404(User, username=username)
    return _do_add(request, other, _safe_next(request, f"/u/{other.username}/"))


@login_required
@require_POST
def friend_respond(request, pk, action):
    """Remove a friend (the only action left now that adding is instant)."""
    f = get_object_or_404(Friendship, pk=pk)
    if action != "unfriend" or request.user.pk not in (f.requester_id, f.addressee_id):
        raise Http404
    other = services.remove_friend(request.user, f)
    messages.success(request, f"أزلتَ @{other.username} من أصدقائك.")
    return redirect(_safe_next(request, "/friends/"))


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


def _day_label(day):
    today = timezone.localdate()
    if day == today:
        return "اليوم"
    if (today - day).days == 1:
        return "أمس"
    return day.strftime("%d/%m/%Y")


def _with_separators(msgs):
    """Messages interleaved with day headings: [{'sep': 'اليوم'}, <Message>, ...]."""
    out = []
    for day, group in groupby(msgs, key=lambda m: timezone.localtime(m.created_at).date()):
        out.append({"sep": _day_label(day)})
        out.extend({"m": m} for m in group)
    return out


@login_required
def thread(request, username):
    other = _friend_or_404(request, username)
    me = request.user
    Message.objects.filter(sender=other, recipient=me, read_at__isnull=True).update(read_at=timezone.now())
    msgs = list(Message.objects.filter(Q(sender=me, recipient=other) | Q(sender=other, recipient=me)).order_by("-id")[:150])[::-1]
    return render(request, "social/thread.html", {
        "other": other, "items": _with_separators(msgs), "last_id": msgs[-1].id if msgs else 0, "nav": "messages",
    })


@login_required
@require_POST
def send(request, username):
    """Send text, a sticker, or an image (with optional caption)."""
    other = _friend_or_404(request, username)
    body = request.POST.get("body", "").strip()[:MAX_BODY]
    sticker = request.POST.get("sticker", "").strip()
    upload = request.FILES.get("image")
    hx = bool(request.headers.get("HX-Request"))

    def done(m=None, error=None):
        if hx:
            if error:
                return HttpResponse(status=204, headers={"HX-Trigger": '{"chat-error": "%s"}' % error})
            return render(request, "social/_bubble.html", {"m": m}) if m else HttpResponse(status=204)
        if error:
            messages.error(request, error)
        return redirect("social:thread", username=username)

    if sticker:
        if len(sticker) > 12 or not EMOJI_ONLY.match(sticker):
            return done(error="ملصق غير صالح.")
        m = Message.objects.create(sender=request.user, recipient=other, kind=Message.STICKER, body=sticker)
        return done(m)
    if upload:
        from django.core.exceptions import ValidationError
        try:
            kind, f = classify(upload)
            if kind != "image":
                raise ValidationError("يمكن إرسال الصور فقط في المحادثة.")
        except ValidationError as e:
            return done(error=e.messages[0])
        m = Message(sender=request.user, recipient=other, kind=Message.IMAGE, body=body)
        m.image.save(f.name, f, save=False)
        m.save()
        return done(m)
    if not body:
        return done()
    return done(Message.objects.create(sender=request.user, recipient=other, body=body))


@login_required
@require_POST
def message_delete(request, pk):
    """Delete my own message for everyone."""
    m = get_object_or_404(Message, pk=pk, sender=request.user)
    m.delete()
    if request.headers.get("HX-Request"):
        return HttpResponse("")
    return redirect("social:thread", username=m.recipient.username)


@login_required
def message_image(request, pk):
    """Chat images are private: only the two people in the conversation can open them."""
    m = get_object_or_404(Message, pk=pk, kind=Message.IMAGE)
    if request.user.pk not in (m.sender_id, m.recipient_id) or not m.image:
        raise Http404
    resp = FileResponse(m.image.open("rb"))
    resp["Cache-Control"] = "private, max-age=3600"
    return resp


@login_required
def poll(request, username):
    """New messages from the other person since `after` (+ read-receipt updates), then a fresh poller."""
    other = _friend_or_404(request, username)
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    new = list(Message.objects.filter(sender=other, recipient=request.user, id__gt=after).order_by("id"))
    if new:
        Message.objects.filter(pk__in=[m.pk for m in new]).update(read_at=timezone.now())
        after = new[-1].id
    recent_reads = Message.objects.filter(
        sender=request.user, recipient=other, read_at__gte=timezone.now() - timedelta(seconds=20)
    )
    return render(request, "social/_poll.html", {"new": new, "other": other, "after": after, "read_now": recent_reads})
