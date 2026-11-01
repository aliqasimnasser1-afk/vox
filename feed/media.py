"""Validation and processing for images and videos attached to posts."""
import io
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".m4v"}
MAX_IMAGE = 8 * 1024 * 1024
MAX_VIDEO = 40 * 1024 * 1024
MAX_SIDE = 1600


def classify(upload):
    """Return ('image'|'video', file) after validating type and size."""
    ext = Path(upload.name).suffix.lower()
    if ext in IMAGE_EXT:
        if upload.size > MAX_IMAGE:
            raise ValidationError("حجم الصورة أكبر من 8 ميجابايت.")
        return "image", _process_image(upload, ext)
    if ext in VIDEO_EXT:
        if upload.size > MAX_VIDEO:
            raise ValidationError("حجم الفيديو أكبر من 40 ميجابايت.")
        return "video", upload
    raise ValidationError("الصيغ المسموحة: صور (jpg, png, webp, gif) أو فيديو (mp4, webm, mov).")


def _process_image(upload, ext):
    """Verify it is a real image, fix orientation, strip metadata (EXIF/GPS) and cap the size."""
    try:
        img = Image.open(upload)
        img.verify()
        upload.seek(0)
        img = Image.open(upload)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("الملف ليس صورة صالحة.")
    if ext == ".gif" and getattr(img, "n_frames", 1) > 1:
        upload.seek(0)
        return upload  # keep animated GIFs untouched
    img = ImageOps.exif_transpose(img)
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    has_alpha = img.mode in ("RGBA", "LA", "P") and "transparency" in img.info or img.mode in ("RGBA", "LA")
    if has_alpha:
        img.convert("RGBA").save(out, "PNG", optimize=True)
        name = Path(upload.name).stem + ".png"
    else:
        img.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
        name = Path(upload.name).stem + ".jpg"
    return ContentFile(out.getvalue(), name=name)
