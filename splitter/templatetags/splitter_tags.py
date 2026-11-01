from django import template

register = template.Library()


@register.filter
def clock(seconds):
    """Seconds -> m:ss or h:mm:ss."""
    s = int(round(float(seconds or 0)))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


@register.filter
def human_len(seconds):
    """Segment length in Arabic words: '30 ثانية' / '2 دقيقة'."""
    s = int(seconds or 0)
    if s % 60 == 0:
        return f"{s // 60} دقيقة"
    return f"{s} ثانية"
