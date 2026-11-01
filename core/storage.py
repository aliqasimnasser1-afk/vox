import mimetypes

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    """Stores files as rows in `core.StoredFile` (used when MEDIA_IN_DB is on)."""

    def _model(self):
        from .models import StoredFile
        return StoredFile

    def _open(self, name, mode="rb"):
        row = self._model().objects.get(name=name)
        return ContentFile(bytes(row.content), name=name)

    def _save(self, name, content):
        data = content.read()
        ctype = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0] or "application/octet-stream"
        self._model().objects.update_or_create(
            name=name, defaults={"content": data, "content_type": ctype, "size": len(data)}
        )
        return name

    def exists(self, name):
        return self._model().objects.filter(name=name).exists()

    def delete(self, name):
        self._model().objects.filter(name=name).delete()

    def size(self, name):
        return self._model().objects.values_list("size", flat=True).get(name=name)

    def url(self, name):
        return settings.MEDIA_URL + name

    def get_available_name(self, name, max_length=None):
        return super().get_available_name(name, max_length)


def local_storage():
    """Always the real filesystem: ffmpeg needs actual paths (video splitter files)."""
    return FileSystemStorage()  # reads MEDIA_ROOT/MEDIA_URL lazily, so overrides (and tests) apply
