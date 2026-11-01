import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
RESERVED = {
    "admin", "administrator", "root", "vox", "support", "help", "staff", "system", "moderator", "mod",
    "login", "logout", "signup", "settings", "api", "static", "media", "messages", "friends", "notifications",
}


def clean_username(value, exclude_pk=None):
    """Normalise and validate a public handle. Raises ValidationError with an Arabic message."""
    name = (value or "").strip().lstrip("@").lower()
    if not USERNAME_RE.match(name):
        raise ValidationError("اسم المستخدم: من 3 إلى 20 حرفاً، إنجليزية صغيرة وأرقام وشرطة سفلية فقط.")
    if name in RESERVED:
        raise ValidationError("اسم المستخدم هذا محجوز.")
    qs = get_user_model().objects.filter(username__iexact=name)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError("اسم المستخدم مستخدم مسبقاً.")
    return name
