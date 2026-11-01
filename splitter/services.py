"""ffmpeg helpers: probe a video and split it into equal-length parts.

Two modes:
  fast    stream copy (no re-encoding). Finishes in seconds even for very long videos, but each cut
          snaps to the nearest keyframe, so part lengths are close to, not exactly, the requested length.
  precise re-encodes every part so cuts are exact. Parts are encoded in parallel on all CPU cores.
"""
import json
import math
import os
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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
            capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
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


def _out_ext(src, mode):
    """Container for the parts. Copy mode keeps the source container family; precise mode is always mp4."""
    if mode == VideoJob.PRECISE:
        return ".mp4"
    suffix = Path(src).suffix.lower()
    if suffix in (".mp4", ".mov", ".m4v"):
        return ".mp4"
    return ".webm" if suffix == ".webm" else ".mkv"


def _last_line(err):
    err.seek(0)
    lines = err.read().strip().splitlines()
    return lines[-1] if lines else "ffmpeg failed"


def _run(cmd):
    """Run ffmpeg, keeping stderr in a file (an unread pipe can fill up and deadlock ffmpeg)."""
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as err:
        code = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err).returncode
        if code != 0:
            raise RuntimeError(_last_line(err))


def _split_fast(job, out_dir, ext):
    seg = job.segment_seconds
    cmd = [
        FFMPEG, "-y", "-nostdin", "-loglevel", "error", "-i", job.source.path,
        "-map", "0:v:0", "-map", "0:a?", "-c", "copy",
        "-f", "segment", "-segment_time", str(seg), "-reset_timestamps", "1", "-segment_start_number", "1",
        "-segment_format_options", "movflags=+faststart",
        "-progress", "pipe:1", "-nostats",
        str(out_dir / f"part_%03d{ext}"),
    ]
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as err:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err, text=True)
        last = 0.0
        for line in proc.stdout:
            key, _, val = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms") and val.isdigit() and job.duration:
                pct = min(99, int(int(val) / 1_000_000 / job.duration * 100))
                if pct != job.progress and time.monotonic() - last > 0.8:
                    job.progress, last = pct, time.monotonic()
                    job.save(update_fields=["progress"])
        if proc.wait() != 0:
            raise RuntimeError(_last_line(err))


def _split_precise(job, out_dir):
    """Encode each part with its own ffmpeg process, several at a time."""
    seg = job.segment_seconds
    total = max(1, math.ceil(job.duration / seg))

    def encode(i):
        _run([
            FFMPEG, "-y", "-nostdin", "-loglevel", "error", "-ss", str(i * seg), "-i", job.source.path,
            "-t", str(seg), "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
            str(out_dir / f"part_{i + 1:03d}.mp4"),
        ])

    workers = max(1, min(os.cpu_count() or 2, 6))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(encode, i) for i in range(total)]):
            fut.result()  # re-raises the first failure
            done += 1
            job.progress = min(99, int(done / total * 100))
            job.save(update_fields=["progress"])


def process_job(job_id):
    job = VideoJob.objects.get(pk=job_id)
    job.status, job.progress, job.error = VideoJob.PROCESSING, 0, ""
    job.save(update_fields=["status", "progress", "error"])

    out_dir = job.parts_dir
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = _out_ext(job.source.name, job.mode)
    seg = job.segment_seconds
    try:
        if job.mode == VideoJob.PRECISE:
            _split_precise(job, out_dir)
        else:
            _split_fast(job, out_dir, ext)

        files = sorted(out_dir.glob("part_*"))
        if not files:
            raise RuntimeError("لم يتم إنتاج أي جزء.")
        parts, start = [], 0.0
        for i, f in enumerate(files):
            dur = probe_duration(f) or 0
            parts.append(VideoPart(job=job, index=i + 1, start=round(start, 2), duration=round(dur, 2),
                                   file=f"splitter/parts/{job.pk}/{f.name}"))
            start += dur if job.mode == VideoJob.FAST else seg
        job.parts.all().delete()
        VideoPart.objects.bulk_create(parts)
        job.status, job.progress = VideoJob.DONE, 100
        job.save(update_fields=["status", "progress"])
    except Exception as exc:  # noqa: BLE001 - record any failure on the job
        shutil.rmtree(out_dir, ignore_errors=True)
        job.status, job.error = VideoJob.FAILED, str(exc)[:300]
        job.save(update_fields=["status", "error"])
