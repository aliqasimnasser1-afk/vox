import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from feed.models import Follow, Notification

from . import services
from .models import Block, Friendship, Message

User = get_user_model()
PW = "S3cure-test-pass!"


def make_user(name):
    return User.objects.create_user(username=name, email=f"{name}@test.dev", password=PW, first_name=name)


def png():
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), (10, 140, 90)).save(buf, "PNG")
    return buf.getvalue()


class FriendTests(TestCase):
    def setUp(self):
        self.me = make_user("me_user")
        self.ann = make_user("ann_k")
        self.client.force_login(self.me)

    def test_adding_is_one_step_and_mutual(self):
        r = self.client.post(reverse("social:friend_add"), {"username": "@Ann_K"})  # case and @ are forgiven
        self.assertEqual(r.status_code, 302)
        f = Friendship.objects.get()
        self.assertEqual(f.status, "accepted")
        self.assertTrue(services.are_friends(self.me, self.ann))
        self.assertTrue(services.are_friends(self.ann, self.me))
        # both follow each other, and the other person is notified
        self.assertTrue(Follow.objects.filter(follower=self.me, followee=self.ann).exists())
        self.assertTrue(Follow.objects.filter(follower=self.ann, followee=self.me).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.ann, kind="friend_added").exists())
        # the other side sees the friend without having to add back
        self.client.force_login(self.ann)
        self.assertContains(self.client.get(reverse("social:friends")), "@me_user")

    def test_add_from_profile_and_buttons(self):
        self.assertContains(self.client.get(reverse("feed:profile", args=["ann_k"])), "إضافة صديق")
        self.client.post(reverse("social:friend_request", args=["ann_k"]), {"next": "/u/ann_k/"})
        html = self.client.get(reverse("feed:profile", args=["ann_k"])).content.decode()
        self.assertIn("رسالة", html)
        self.assertNotIn("إضافة صديق", html)

    def test_unknown_self_and_duplicate(self):
        self.assertContains(self.client.post(reverse("social:friend_add"), {"username": "nobody"}, follow=True), "لا يوجد مستخدم")
        self.client.post(reverse("social:friend_add"), {"username": "me_user"})
        self.assertEqual(Friendship.objects.count(), 0)
        self.client.post(reverse("social:friend_add"), {"username": "ann_k"})
        self.client.post(reverse("social:friend_add"), {"username": "ann_k"})
        self.assertEqual(Friendship.objects.count(), 1)

    def test_remove_blocks_readding_until_remover_adds_back(self):
        services.add_friend(self.me, self.ann)
        f = Friendship.objects.get()
        self.client.post(reverse("social:friend_respond", args=[f.pk, "unfriend"]))
        self.assertEqual(Friendship.objects.count(), 0)
        self.assertEqual(Follow.objects.count(), 0)
        self.assertTrue(Block.objects.filter(blocker=self.me, blocked=self.ann).exists())

        self.client.force_login(self.ann)  # the removed person cannot add me again
        self.client.post(reverse("social:friend_add"), {"username": "me_user"})
        self.assertEqual(Friendship.objects.count(), 0)

        self.client.force_login(self.me)  # but I can, which lifts the block
        self.client.post(reverse("social:friend_add"), {"username": "ann_k"})
        self.assertEqual(Friendship.objects.count(), 1)
        self.assertFalse(Block.objects.exists())

    def test_only_participants_can_remove(self):
        services.add_friend(self.me, self.ann)
        f = Friendship.objects.get()
        self.client.force_login(make_user("zed_z"))
        self.assertEqual(self.client.post(reverse("social:friend_respond", args=[f.pk, "unfriend"])).status_code, 404)
        self.assertEqual(Friendship.objects.count(), 1)

    def test_legacy_pending_request_becomes_friendship_when_added(self):
        Friendship.objects.create(requester=self.ann, addressee=self.me, status="pending")
        self.assertFalse(services.are_friends(self.me, self.ann))
        self.client.post(reverse("social:friend_add"), {"username": "ann_k"})
        self.assertEqual(Friendship.objects.get().status, "accepted")


class MessageTests(TestCase):
    def setUp(self):
        self.me = make_user("me_user")
        self.ann = make_user("ann_k")
        self.zed = make_user("zed_z")
        services.add_friend(self.me, self.ann)
        self.client.force_login(self.me)

    def test_send_text_and_read(self):
        r = self.client.post(reverse("social:send", args=["ann_k"]), {"body": "  hello  "}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "hello")
        m = Message.objects.get()
        self.assertEqual((m.sender, m.recipient, m.body, m.kind), (self.me, self.ann, "hello", "text"))
        self.assertIsNone(m.read_at)
        self.client.force_login(self.ann)
        self.assertContains(self.client.get(reverse("social:inbox")), "hello")
        self.client.get(reverse("social:thread", args=["me_user"]))
        m.refresh_from_db()
        self.assertIsNotNone(m.read_at)

    def test_only_friends_can_message(self):
        self.assertEqual(self.client.get(reverse("social:thread", args=["zed_z"])).status_code, 404)
        self.assertEqual(self.client.post(reverse("social:send", args=["zed_z"]), {"body": "hi"}).status_code, 404)
        self.assertEqual(Message.objects.count(), 0)

    def test_empty_and_long_bodies(self):
        self.client.post(reverse("social:send", args=["ann_k"]), {"body": "   "})
        self.assertEqual(Message.objects.count(), 0)
        self.client.post(reverse("social:send", args=["ann_k"]), {"body": "x" * 5000})
        self.assertEqual(len(Message.objects.get().body), 1000)

    def test_stickers(self):
        r = self.client.post(reverse("social:send", args=["ann_k"]), {"sticker": "🎉"}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "sticker-face")
        m = Message.objects.get()
        self.assertEqual((m.kind, m.body), ("sticker", "🎉"))
        self.client.post(reverse("social:send", args=["ann_k"]), {"sticker": "<script>"})
        self.client.post(reverse("social:send", args=["ann_k"]), {"sticker": "hello world"})
        self.assertEqual(Message.objects.count(), 1)  # only real emoji are accepted as stickers

    def test_emoji_only_text_is_big(self):
        r = self.client.post(reverse("social:send", args=["ann_k"]), {"body": "😂😂"}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "emoji-only")
        r = self.client.post(reverse("social:send", args=["ann_k"]), {"body": "hi 😂"}, HTTP_HX_REQUEST="true")
        self.assertNotContains(r, "emoji-only")

    def test_image_message_is_private(self):
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=tmp):
                r = self.client.post(reverse("social:send", args=["ann_k"]), {
                    "body": "look", "image": SimpleUploadedFile("p.png", png(), content_type="image/png")}, HTTP_HX_REQUEST="true")
                self.assertContains(r, "chat-img")
                m = Message.objects.get()
                self.assertEqual(m.kind, "image")
                url = reverse("social:message_image", args=[m.pk])
                self.assertEqual(self.client.get(url).status_code, 200)       # sender
                self.client.force_login(self.ann)
                self.assertEqual(self.client.get(url).status_code, 200)       # recipient
                self.client.force_login(self.zed)
                self.assertEqual(self.client.get(url).status_code, 404)       # nobody else
                self.client.logout()
                self.assertEqual(self.client.get(url).status_code, 302)
                # bad uploads are rejected
                self.client.force_login(self.me)
                self.client.post(reverse("social:send", args=["ann_k"]), {"image": SimpleUploadedFile("x.png", b"nope")})
                self.client.post(reverse("social:send", args=["ann_k"]), {"image": SimpleUploadedFile("x.mp4", b"0000")})
                self.assertEqual(Message.objects.count(), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_own_message_only(self):
        m = Message.objects.create(sender=self.me, recipient=self.ann, body="oops")
        other = Message.objects.create(sender=self.ann, recipient=self.me, body="theirs")
        self.assertEqual(self.client.post(reverse("social:message_delete", args=[other.pk])).status_code, 404)
        r = self.client.post(reverse("social:message_delete", args=[m.pk]), HTTP_HX_REQUEST="true")
        self.assertEqual(r.content, b"")
        self.assertEqual(Message.objects.count(), 1)

    def test_poll_new_messages_and_read_receipts(self):
        a = Message.objects.create(sender=self.ann, recipient=self.me, body="one")
        mine = Message.objects.create(sender=self.me, recipient=self.ann, body="mine", read_at=timezone.now())
        r = self.client.get(reverse("social:poll", args=["ann_k"]) + f"?after={a.id - 1}")
        self.assertContains(r, "one")
        self.assertContains(r, f'id="tick-{mine.id}"')       # live "read" update for my message
        again = self.client.get(reverse("social:poll", args=["ann_k"]) + f"?after={a.id}")
        self.assertNotContains(again, ">one<")

    def test_ticks_and_day_separator(self):
        Message.objects.create(sender=self.me, recipient=self.ann, body="sent")
        html = self.client.get(reverse("social:thread", args=["ann_k"])).content.decode()
        self.assertIn("اليوم", html)
        self.assertIn('class="ticks"', html)  # delivered, not read yet

    def test_third_party_cannot_read(self):
        Message.objects.create(sender=self.ann, recipient=self.me, body="secret text")
        self.client.force_login(self.zed)
        self.assertEqual(self.client.get(reverse("social:thread", args=["ann_k"])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("social:inbox")), "secret text")

    def test_unread_badge_counts_and_preview(self):
        Message.objects.create(sender=self.ann, recipient=self.me, kind="sticker", body="🎉")
        r = self.client.get(reverse("feed:home"))
        self.assertEqual(r.context["unread_messages_count"], 1)
        self.assertContains(self.client.get(reverse("social:inbox")), "ملصق")
