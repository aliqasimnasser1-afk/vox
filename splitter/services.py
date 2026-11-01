"""ffmpeg helpers: probe a video and split it into equal-length parts."""
import json
import shutil
import subprocess
import tempfile
import threading
import time

from django.db import close_old_connections

from .models import VideoJob, VideoPart

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")

_running = set()  # job ids with a live worker thread in this process
_lock = threading.Lock()


def tools_available():
    return bool(FFMPEG and FFPROBE)


def probe_duration(path):
    """Duration in seconds, or None when the file is not a readable video."""
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        return float(json.loads(out.stdout)["format"]["duration"])
    except (subprocess.SubprocessError, KeyError, ValueError, TypeError, OSError):
        return None


def is_running(job_id):
    with _lock:
        return job_id in _running


def start_job(job_id):
    """Run the split in a background thread so the request returns immediately."""
    with _lock:
        _running.add(job_id)
    threading.Thread(target=_worker, args=(job_id,), daemon=True).start()


def _worker(job_id):
    try:
        process_job(job_id)
    finally:
        with _lock:
            _running.discard(job_id)
        close_old_connections()


def process_job(job_id):
    """Split the source into `segment_seconds` parts. Re-encodes so every cut is exact."""
    job = VideoJob.objects.get(pk=job_id)
    job.status, job.progress, job.error = VideoJob.PROCESSING, 0, ""
    job.save(update_fields=["status", "progress", "error"])

    out_dir = job.parts_dir
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    seg = job.segment_seconds

    cmd = [
        FFMPEG, "-y", "-nostdin", "-loglevel", "error", "-i", job.source.path,
        "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-force_key_frames", f"expr:gte(t,n_forced*{seg})",
        "-f", "segment", "-segment_time", str(seg), "-reset_timestamps", "1",
        "-segment_start_number", "1", "-segment_format_options", "movflags=+faststart",
        "-progress", "pipe:1", "-nostats",
        str(out_dir / "part_%03d.mp4"),
    ]
    try:
        # stderr goes to a file: an unread pipe fills up and deadlocks ffmpeg.
        errfile = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errfile, text=True)
        last = 0.0
        for line in proc.stdout:
            key, _, val = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms") and val.isdigit() and job.duration:
                pct = min(99, int(int(val) / 1_000_000 / job.duration * 100))
                if pct != job.progress and time.monotonic() - last > 0.8:
                    job.progress, last = pct, time.monotonic()
                    job.save(update_fields=["progress"])
        code = proc.wait()
        errfile.seek(0)
        err = errfile.read()
        errfile.close()
        if code != 0:
            raise RuntimeError(err.strip().splitlines()[-1] if err.strip() else "ffmpeg failed")

        files = sorted(out_dir.glob("part_*.mp4"))
        if not files:
            raise RuntimeError("لم يتم إنتاج أي جزء.")
        parts = []
        for i, f in enumerate(files):
            dur = probe_duration(f) or 0
            parts.append(VideoPart(
                job=job, index=i + 1, start=i * seg, duration=round(dur, 2),
                file=f"splitter/parts/{job.pk}/{f.name}",
            ))
        job.parts.all().delete()
        VideoPart.objects.bulk_create(parts)
        job.status, job.progress = VideoJob.DONE, 100
        job.save(update_fields=["status", "progress"])
    except Exception as exc:  # noqa: BLE001 - record any failure on the job
        shutil.rmtree(out_dir, ignore_errors=True)
        job.status, job.error = VideoJob.FAILED, str(exc)[:300]
        job.save(update_fields=["status", "error"])
