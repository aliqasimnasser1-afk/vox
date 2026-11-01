"""Hashtag parsing, rendering and trending."""
import re
from datetime import timedelta

from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe

# '#' not glued to a word, an HTML entity (&#x27;) or a URL path (/#anchor), then 2-50 word characters (Arabic included).
TAG_RE = re.compile(r"(?<![\w&#/])#(\w{2,50})")
MAX_TAGS = 10


def _valid(tag):
    return any(c.isalpha() for c in tag)  # '#123' and '#__' are not hashtags


def extract(text):
    """Lower-cased unique hashtag names in order of appearance."""
    seen, out = set(), []
    for m in TAG_RE.finditer(text or ""):
        tag = m.group(1).lower()
        if tag not in seen and _valid(tag):
            seen.add(tag)
            out.append(tag)
    return out[:MAX_TAGS]


def attach(post):
    """Create missing Hashtag rows and link them to the post."""
    from .models import Hashtag
    tags = [Hashtag.objects.get_or_create(name=n)[0] for n in extract(post.content)]
    post.hashtags.set(tags)


def linkify(text):
    """Escape the text, then turn #tags into links. Safe against HTML injection."""
    def repl(m):
        tag = m.group(1)
        if not _valid(tag):
            return m.group(0)
        url = reverse("feed:tag", args=[tag.lower()])
        return f'<a href="{url}" class="hashtag">#{tag}</a>'
    return mark_safe(TAG_RE.sub(repl, escape(text or "")))


def trending(limit=8):
    """Hashtags used in the most posts over the last 24 hours (widening to 7 days when it is quiet)."""
    from .models import Hashtag
    now = timezone.now()
    for window in (timedelta(hours=24), timedelta(days=7)):
        qs = (Hashtag.objects.filter(posts__created_at__gte=now - window)
              .annotate(n=Count("posts", distinct=True)).order_by("-n", "name")[:limit])
        rows = list(qs)
        if len(rows) >= 3 or window == timedelta(days=7):
            return rows
    return []
