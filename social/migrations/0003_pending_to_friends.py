"""Friend requests no longer need approval: turn pending ones into friendships (and make both sides follow)."""
from django.db import migrations


def accept_pending(apps, schema_editor):
    Friendship = apps.get_model("social", "Friendship")
    Follow = apps.get_model("feed", "Follow")
    Notification = apps.get_model("feed", "Notification")
    for f in Friendship.objects.filter(status="pending"):
        f.status = "accepted"
        f.save(update_fields=["status"])
        Follow.objects.get_or_create(follower_id=f.requester_id, followee_id=f.addressee_id)
        Follow.objects.get_or_create(follower_id=f.addressee_id, followee_id=f.requester_id)
    Notification.objects.filter(kind="friend_request").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("social", "0002_chat_and_instant_friends"),
        ("feed", "0006_chat_and_instant_friends"),
    ]
    operations = [migrations.RunPython(accept_pending, migrations.RunPython.noop)]
