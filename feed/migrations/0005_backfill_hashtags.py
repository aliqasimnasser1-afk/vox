"""Link hashtags for posts that were published before hashtags existed."""
import re

from django.db import migrations

TAG_RE = re.compile(r"(?<![\w&#])#(\w{2,50})")


def backfill(apps, schema_editor):
    Post = apps.get_model("feed", "Post")
    Hashtag = apps.get_model("feed", "Hashtag")
    for post in Post.objects.exclude(content="").iterator():
        seen, tags = set(), []
        for m in TAG_RE.finditer(post.content):
            t = m.group(1).lower()
            if t not in seen and any(c.isalpha() for c in t):
                seen.add(t)
                tags.append(t)
        if tags:
            post.hashtags.set([Hashtag.objects.get_or_create(name=t)[0] for t in tags[:10]])


class Migration(migrations.Migration):
    dependencies = [("feed", "0004_hashtags")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
