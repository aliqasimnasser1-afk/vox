"""Usernames used to be generated from the email's local part, which leaked part of the email.
Rename every such account to a neutral handle; users can pick their own in the profile editor."""
import random
import re

from django.db import migrations


def rename(apps, schema_editor):
    User = apps.get_model("auth", "User")
    taken = set(User.objects.values_list("username", flat=True))
    for u in User.objects.exclude(email=""):
        local = re.sub(r"[^a-z0-9_]", "", u.email.split("@")[0].lower())[:14]
        if len(local) < 3:
            local = "user" + local
        if not u.username.lower().startswith(local):
            continue  # the user already chose something unrelated to their email
        for _ in range(50):
            candidate = f"user{random.randint(100000, 999999)}"
            if candidate not in taken:
                break
        taken.add(candidate)
        u.username = candidate
        u.save(update_fields=["username"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_profile_avatar_profile_location_profile_website"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(rename, migrations.RunPython.noop)]
