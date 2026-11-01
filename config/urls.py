from django.contrib import admin
from django.urls import include, path, re_path

from core.views import media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("splitter.urls")),
    path("", include("social.urls")),
    path("", include("feed.urls")),
    # Avatars and post media are public. Video-splitter files are served only by an owner-only view.
    re_path(r"^media/(?P<path>.+)$", media),
]
