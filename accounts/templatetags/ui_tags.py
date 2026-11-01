from django import template

register = template.Library()


@register.filter
def hue(value):
    """Stable 0-359 hue from a username so every avatar gets its own colour."""
    return sum(ord(c) * (i + 3) for i, c in enumerate(str(value))) % 360
