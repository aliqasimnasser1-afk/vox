import math
import tempfile
import zipfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import MAX_PARTS, SplitForm
from .models import VideoJob


def _own_job(request, job_id):
    return get_object_or_404(VideoJob, pk=job_id, user=request.user)


def _settle(job):
    """A job left 'active' by a restarted server has no worker; mark it failed instead of spinning forever."""
    if job.active and not services.is_running(job.pk):
        job.status, job.error = VideoJob.FAILED, "توقفت المعالجة (أُعيد تشغيل الخادم). أعد المحاولة."
        job.save(update_fields=["status", "error"])


@login_required
def index(request):
    form = SplitForm(request.POST or None, request.FILES or None)
    available = services.tools_available()
    if request.method == "POST" and available and form.is_valid():
        seg = form.segment_seconds
        video = form.cleaned_data["video"]
        job = VideoJob.objects.create(user=request.user, title=video.name[:200], source=video, segment_seconds=seg)
        duration = services.probe_duration(job.source.path)
        if not duration:
            job.delete_files(); job.delete()
            form.add_error("video", "تعذّرت قراءة الفيديو. تأكد أن الملف سليم.")
        elif math.ceil(duration / seg) > MAX_PARTS:
            job.delete_files(); job.delete()
            form.add_error("amount", f"عدد الأجزاء سيتجاوز {MAX_PARTS}. اختر طولاً أكبر.")
        else:
            job.duration = duration
            job.save(update_fields=["duration"])
            services.start_job(job.pk)
            return redirect("splitter:detail", job_id=job.pk)
    jobs = list(VideoJob.objects.filter(user=request.user)[:20])
    for j in jobs:
        _settle(j)
    return render(request, "splitter/index.html", {
        "form": form, "jobs": jobs, "available": available, "nav": "splitter",
    })


@login_required
def detail(request, job_id):
    job = _own_job(request, job_id)
    _settle(job)
    return render(request, "splitter/detail.html", {"job": job, "nav": "splitter"})


@login_required
def status(request, job_id):
    job = _own_job(request, job_id)
    _settle(job)
    return render(request, "splitter/_job_body.html", {"job": job})


@login_required
@require_POST
def retry(request, job_id):
    job = _own_job(request, job_id)
    if job.status == VideoJob.FAILED and job.source and services.tools_available():
        job.status, job.progress, job.error = VideoJob.PENDING, 0, ""
        job.save(update_fields=["status", "progress", "error"])
        services.start_job(job.pk)
    return redirect("splitter:detail", job_id=job.pk)


@login_required
@require_POST
def delete(request, job_id):
    job = _own_job(request, job_id)
    if services.is_running(job.pk):
        messages.error(request, "لا يمكن الحذف أثناء التقسيم.")
        return redirect("splitter:detail", job_id=job.pk)
    job.delete_files()
    job.delete()
    messages.success(request, "تم حذف الفيديو وأجزائه.")
    return redirect("splitter:index")


@login_required
def download_zip(request, job_id):
    job = _own_job(request, job_id)
    if job.status != VideoJob.DONE:
        return redirect("splitter:detail", job_id=job.pk)
    tmp = tempfile.TemporaryFile()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:  # videos are already compressed
        for p in job.parts.all():
            z.write(p.file.path, arcname=f"part_{p.index:03d}.mp4")
    tmp.seek(0)
    return FileResponse(tmp, as_attachment=True, filename=f"video_parts_{job.pk}.zip")
