from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("splitter.urls")),
    path("", include("feed.urls")),
    # Only avatars are public. Uploaded videos and their parts are served by an
    # authenticated, owner-only view in the splitter app.
    re_path(r"^media/(?P<path>avatars/.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
