"""Chunked uploads for the video splitter.

Many hosts cap a single request body (PythonAnywhere: 100 MB, answered by an nginx "413 Request Entity
Too Large"). The browser therefore cuts a big video into small chunks, sends them one by one, and then asks
the server to assemble the file and start the split.
"""
import json
import math
import re
import shutil
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import services
from .forms import ALLOWED, MAX_BYTES, MAX_PARTS, SplitParamsForm
from .models import VideoJob

CHUNK_SIZE = 16 * 1024 * 1024            # what the browser sends per request
STALE_AFTER = 6 * 3600                   # abandoned uploads are deleted after 6 hours
UID_RE = re.compile(r"^[0-9a-f]{32}$")


def _tmp_root(user):
    return Path(settings.MEDIA_ROOT) / "splitter" / "tmp" / str(user.pk)


def _clean_stale(root):
    if not root.exists():
        return
    now = time.time()
    for d in root.iterdir():
        if d.is_dir() and now - d.stat().st_mtime > STALE_AFTER:
            shutil.rmtree(d, ignore_errors=True)


def _session(request, uid):
    """The upload folder and its metadata for this user, or None."""
    if not UID_RE.match(uid or ""):
        return None, None
    folder = _tmp_root(request.user) / uid
    meta_file = folder / "meta.json"
    if not meta_file.is_file():
        return None, None
    return folder, json.loads(meta_file.read_text(encoding="utf-8"))


def _err(message, status=400):
    return JsonResponse({"error": message}, status=status)


@login_required
@require_POST
def init(request):
    if not services.tools_available():
        return _err("أداة ffmpeg غير مثبّتة على الخادم.")
    name = Path(request.POST.get("name", "")).name[:200]
    try:
        size = int(request.POST.get("size", 0))
    except ValueError:
        size = 0
    if Path(name).suffix.lower() not in ALLOWED:
        return _err("صيغة غير مدعومة. المسموح: " + "، ".join(sorted(e[1:] for e in ALLOWED)))
    if size <= 0:
        return _err("الملف فارغ.")
    if size > MAX_BYTES:
        return _err(f"حجم الفيديو أكبر من {MAX_BYTES // (1024 * 1024)} ميجابايت.")
    root = _tmp_root(request.user)
    _clean_stale(root)
    uid = uuid.uuid4().hex
    folder = root / uid
    folder.mkdir(parents=True)
    (folder / "meta.json").write_text(json.dumps({"name": name, "size": size}), encoding="utf-8")
    return JsonResponse({"id": uid, "chunk_size": CHUNK_SIZE, "chunks": math.ceil(size / CHUNK_SIZE)})


@login_required
@require_POST
def chunk(request):
    folder, meta = _session(request, request.POST.get("id", ""))
    if not folder:
        return _err("جلسة الرفع غير موجودة أو انتهت.", 404)
    total = math.ceil(meta["size"] / CHUNK_SIZE)
    try:
        index = int(request.POST.get("index", -1))
    except ValueError:
        index = -1
    blob = request.FILES.get("chunk")
    if not blob or not 0 <= index < total:
        return _err("جزء غير صالح.")
    if blob.size > CHUNK_SIZE:
        return _err("الجزء أكبر من المسموح.")
    with open(folder / f"part_{index:05d}", "wb") as out:
        for piece in blob.chunks():
            out.write(piece)
    folder.touch()
    return JsonResponse({"ok": True, "index": index})


@login_required
@require_POST
def finish(request):
    folder, meta = _session(request, request.POST.get("id", ""))
    if not folder:
        return _err("جلسة الرفع غير موجودة أو انتهت.", 404)
    form = SplitParamsForm(request.POST)
    if not form.is_valid():
        first = next(iter(form.errors.values()))[0]
        return _err(first)

    total = math.ceil(meta["size"] / CHUNK_SIZE)
    parts = [folder / f"part_{i:05d}" for i in range(total)]
    if not all(p.is_file() for p in parts) or sum(p.stat().st_size for p in parts) != meta["size"]:
        return _err("لم تصل كل أجزاء الملف. أعد المحاولة.")

    ext = Path(meta["name"]).suffix.lower()
    rel = f"splitter/sources/{request.user.pk}/{uuid.uuid4().hex}{ext}"
    dest = Path(settings.MEDIA_ROOT) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as out:
        for p in parts:
            with open(p, "rb") as src:
                shutil.copyfileobj(src, out, 1024 * 1024)
    shutil.rmtree(folder, ignore_errors=True)

    seg = form.segment_seconds
    duration = services.probe_duration(dest)
    if not duration:
        dest.unlink(missing_ok=True)
        return _err("تعذّرت قراءة الفيديو. تأكد أن الملف سليم.")
    if math.ceil(duration / seg) > MAX_PARTS:
        dest.unlink(missing_ok=True)
        return _err(f"عدد الأجزاء سيتجاوز {MAX_PARTS}. اختر طولاً أكبر.")

    job = VideoJob(user=request.user, title=meta["name"][:200], segment_seconds=seg,
                   mode=form.cleaned_data["mode"], duration=duration)
    job.source.name = rel
    job.save()
    services.start_job(job.pk)
    return JsonResponse({"redirect": reverse("splitter:detail", args=[job.pk])})


@login_required
@require_POST
def abort(request):
    """Drop a half-finished upload (the browser calls this when the user cancels or it fails)."""
    folder, _ = _session(request, request.POST.get("id", ""))
    if folder:
        shutil.rmtree(folder, ignore_errors=True)
    return JsonResponse({"ok": True})
