from django import template

from feed.hashtags import linkify

register = template.Library()


@register.filter
def with_tags(text):
    """Post text with clickable #hashtags (HTML-escaped first)."""
    return linkify(text)
