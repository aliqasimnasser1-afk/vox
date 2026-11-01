from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PostForm
from .models import Follow, Like, Post

User = get_user_model()
PAGE_SIZE = 20


def annotated(qs, user):
    """Posts with like counts and whether `user` liked each one (no N+1 queries)."""
    return qs.select_related("author", "author__profile").annotate(
        like_count=Count("likes", distinct=True),
        liked=Exists(Like.objects.filter(post=OuterRef("pk"), user=user)),
    ).order_by("-created_at", "-id")  # annotate() drops Meta.ordering on grouped queries


def paginate(request, qs):
    return Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))


@login_required
def home(request):
    tab = "following" if request.GET.get("tab") == "following" else "all"
    posts = Post.objects.all()
    if tab == "following":
        ids = list(request.user.following.values_list("followee_id", flat=True)) + [request.user.id]
        posts = posts.filter(author_id__in=ids)
    page = paginate(request, annotated(posts, request.user))
    return render(request, "feed/home.html", {"page": page, "tab": tab, "form": PostForm()})


@login_required
@require_POST
def post_create(request):
    form = PostForm(request.POST)
    if form.is_valid():
        Post.objects.create(author=request.user, content=form.cleaned_data["content"])
    else:
        messages.error(request, "التغريدة فارغة أو أطول من 280 حرفاً.")
    return redirect(request.POST.get("next") if request.POST.get("next", "").startswith("/") else "feed:home")


def _render_post(request, post_id):
    post = annotated(Post.objects.filter(pk=post_id), request.user).first()
    return render(request, "feed/_post.html", {"post": post})


@login_required
@require_POST
def like_toggle(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    if request.headers.get("HX-Request"):
        return _render_post(request, post.pk)
    return redirect(request.META.get("HTTP_REFERER", "feed:home"))


@login_required
@require_POST
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    post.delete()
    if request.headers.get("HX-Request"):
        return HttpResponse("")
    return redirect(request.META.get("HTTP_REFERER", "feed:home"))


@login_required
def profile(request, username):
    owner = get_object_or_404(User.objects.select_related("profile"), username=username)
    return render(request, "feed/profile.html", {
        "owner": owner,
        "page": paginate(request, annotated(owner.posts.all(), request.user)),
        "is_following": Follow.objects.filter(follower=request.user, followee=owner).exists(),
        "followers_count": owner.followers.count(),
        "following_count": owner.following.count(),
    })


@login_required
@require_POST
def follow_toggle(request, username):
    target = get_object_or_404(User, username=username)
    if target != request.user:
        follow, created = Follow.objects.get_or_create(follower=request.user, followee=target)
        if not created:
            follow.delete()
    return redirect("feed:profile", username=username)
