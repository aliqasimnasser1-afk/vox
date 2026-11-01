from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import LoginForm, ProfileForm, SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("feed:home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.EmailBackend")
        return redirect("feed:home")
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("feed:home")
    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user, backend="accounts.backends.EmailBackend")
        nxt = request.GET.get("next", "")
        return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else "feed:home")
    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ الملف الشخصي.")
        return redirect("feed:profile", username=request.user.username)
    return render(request, "accounts/profile_edit.html", {"form": form})
