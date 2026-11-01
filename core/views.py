import re
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from .models import StoredFile

PUBLIC_PREFIXES = ("avatars/", "posts/")


def _range(request, data, ctype):
    size = len(data)
    m = re.match(r"bytes=(\d*)-(\d*)$", request.headers.get("Range", ""))
    if not m or not (m.group(1) or m.group(2)):
        resp = HttpResponse(data, content_type=ctype)
    else:
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
        end = min(int(m.group(2)), size - 1) if m.group(1) and m.group(2) else size - 1
        if start > end or start >= size:
            return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
        resp = HttpResponse(data[start:end + 1], status=206, content_type=ctype)
        resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    resp["Accept-Ranges"] = "bytes"
    return resp


@require_GET
@cache_control(public=True, max_age=86400)
def media(request, path):
    """Serve avatars and post media. Video-splitter files are never served here."""
    if not path.startswith(PUBLIC_PREFIXES) or ".." in path:
        raise Http404
    if settings.MEDIA_IN_DB:
        try:
            row = StoredFile.objects.get(name=path)
        except StoredFile.DoesNotExist:
            raise Http404
        return _range(request, bytes(row.content), row.content_type)
    full = Path(settings.MEDIA_ROOT) / path
    if not full.is_file():
        raise Http404
    return _range(request, full.read_bytes(), __import__("mimetypes").guess_type(str(full))[0] or "application/octet-stream")
