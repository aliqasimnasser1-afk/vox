from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PostForm
from .models import Bookmark, Follow, Like, Notification, Post
from .notifications import notify, unnotify


def friend_status(viewer, other):
    from social.services import status_for
    return status_for(viewer, other)


def friendship_between(viewer, other):
    from social.services import between
    return between(viewer, other)

User = get_user_model()
PAGE_SIZE = 20


def annotated(qs, user):
    """Posts with like count plus liked/bookmarked flags for `user` (no N+1 queries)."""
    return qs.select_related("author", "author__profile").annotate(
        like_count=Count("likes", distinct=True),
        liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user)),
        bookmarked=Exists(Bookmark.objects.filter(post=OuterRef("pk"), user=user)),
    ).order_by("-created_at", "-id")  # annotate() drops Meta.ordering on grouped queries


def paginate(request, qs):
    return Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))


def safe_next(request, default="feed:home"):
    nxt = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else default


@login_required
def home(request):
    tab = "following" if request.GET.get("tab") == "following" else "all"
    posts = Post.objects.all()
    if tab == "following":
        ids = list(request.user.following.values_list("followee_id", flat=True)) + [request.user.id]
        posts = posts.filter(author_id__in=ids)
    page = paginate(request, annotated(posts, request.user))
    return render(request, "feed/home.html", {"page": page, "tab": tab, "form": PostForm(), "nav": "home"})


@login_required
@require_POST
def post_create(request):
    form = PostForm(request.POST, request.FILES)
    if form.is_valid():
        post = Post(author=request.user, content=form.cleaned_data["content"])
        media = form.cleaned_data["media"]
        if media:
            kind, f = media
            getattr(post, kind).save(f.name, f, save=False)
        post.save()
        messages.success(request, "تم نشر التغريدة.")
    else:
        errs = [e for field in form.errors.values() for e in field]
        messages.error(request, errs[0] if errs else "تعذّر النشر.")
    return redirect("feed:home")


@login_required
def post_detail(request, post_id):
    post = get_object_or_404(annotated(Post.objects.all(), request.user), pk=post_id)
    return render(request, "feed/post_detail.html", {"post": post, "nav": ""})


def _render_post(request, post_id):
    post = annotated(Post.objects.filter(pk=post_id), request.user).first()
    return render(request, "feed/_post.html", {"post": post})


def _hx(request):
    return bool(request.headers.get("HX-Request"))


@login_required
@require_POST
def like_toggle(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if created:
        notify(post.author, request.user, Notification.LIKE, post)
    else:
        like.delete()
        unnotify(post.author, request.user, Notification.LIKE, post)
    return _render_post(request, post.pk) if _hx(request) else redirect(safe_next(request))


@login_required
@require_POST
def bookmark_toggle(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    bm, created = Bookmark.objects.get_or_create(user=request.user, post=post)
    if not created:
        bm.delete()
    if _hx(request):
        # On the favorites page an un-saved post disappears from the list.
        if not created and "/bookmarks/" in request.headers.get("HX-Current-URL", ""):
            return HttpResponse("")
        return _render_post(request, post.pk)
    return redirect(safe_next(request))


@login_required
@require_POST
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    post.delete()
    if _hx(request):
        return HttpResponse("")
    return redirect("feed:home")


@login_required
def bookmarks(request):
    ids = Bookmark.objects.filter(user=request.user).values("post_id")
    qs = annotated(Post.objects.filter(pk__in=ids), request.user)
    # Newest saved first.
    order = {b: i for i, b in enumerate(Bookmark.objects.filter(user=request.user).values_list("post_id", flat=True))}
    page = paginate(request, qs)
    page.object_list = sorted(page.object_list, key=lambda p: order.get(p.pk, 0))
    return render(request, "feed/bookmarks.html", {"page": page, "nav": "bookmarks"})


@login_required
def notifications(request):
    items = list(
        Notification.objects.filter(recipient=request.user)
        .select_related("actor", "actor__profile", "post")[:100]
    )
    unread_ids = [n.pk for n in items if not n.is_read]
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids).update(is_read=True)
        # The sidebar badge was computed before this update; correct it for this render.
    return render(request, "feed/notifications.html", {
        "items": items, "unread_ids": set(unread_ids), "nav": "notifications", "unread_count": 0,
    })


@login_required
def notification_badge(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, "feed/_badge.html", {"unread_count": count})


@login_required
def profile(request, username):
    owner = get_object_or_404(User.objects.select_related("profile"), username=username)
    tab = "likes" if request.GET.get("tab") == "likes" else "posts"
    if tab == "likes":
        liked_ids = Like.objects.filter(user=owner).values("post_id")
        qs = Post.objects.filter(pk__in=liked_ids)
    else:
        qs = owner.posts.all()
    return render(request, "feed/profile.html", {
        "owner": owner,
        "tab": tab,
        "page": paginate(request, annotated(qs, request.user)),
        "is_following": Follow.objects.filter(follower=request.user, followee=owner).exists(),
        "friend_status": friend_status(request.user, owner),
        "friendship": friendship_between(request.user, owner),
        "followers_count": owner.followers.count(),
        "following_count": owner.following.count(),
        "posts_count": owner.posts.count(),
        "nav": "profile" if owner == request.user else "",
    })


@login_required
def follow_list(request, username, kind):
    owner = get_object_or_404(User.objects.select_related("profile"), username=username)
    if kind == "followers":
        rows = owner.followers.select_related("follower", "follower__profile")
        users = [r.follower for r in rows]
    else:
        rows = owner.following.select_related("followee", "followee__profile")
        users = [r.followee for r in rows]
    mine = set(request.user.following.values_list("followee_id", flat=True))
    return render(request, "feed/follow_list.html", {
        "owner": owner, "users": users, "kind": kind, "mine": mine, "nav": "",
    })


@login_required
@require_POST
def follow_toggle(request, username):
    target = get_object_or_404(User, username=username)
    if target != request.user:
        follow, created = Follow.objects.get_or_create(follower=request.user, followee=target)
        if created:
            notify(target, request.user, Notification.FOLLOW)
        else:
            follow.delete()
            unnotify(target, request.user, Notification.FOLLOW)
    nxt = request.POST.get("next", "")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("feed:profile", username=username)
