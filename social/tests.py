from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from feed.models import Notification

from . import services
from .models import Friendship, Message

User = get_user_model()
PW = "S3cure-test-pass!"


def make_user(name):
    return User.objects.create_user(username=name, email=f"{name}@test.dev", password=PW, first_name=name)


class FriendTests(TestCase):
    def setUp(self):
        self.me = make_user("me")
        self.ann = make_user("ann")
        self.client.force_login(self.me)

    def test_add_by_username_then_accept(self):
        r = self.client.post(reverse("social:friend_add"), {"username": "@Ann"})  # case and @ are forgiven
        self.assertEqual(r.status_code, 302)
        f = Friendship.objects.get()
        self.assertEqual((f.requester, f.addressee, f.status), (self.me, self.ann, "pending"))
        self.assertTrue(Notification.objects.filter(recipient=self.ann, kind="friend_request").exists())

        self.client.force_login(self.ann)
        self.assertContains(self.client.get(reverse("social:friends") + "?tab=requests"), "@me")
        self.client.post(reverse("social:friend_respond", args=[f.pk, "accept"]))
        f.refresh_from_db()
        self.assertEqual(f.status, "accepted")
        self.assertTrue(services.are_friends(self.me, self.ann))
        self.assertTrue(Notification.objects.filter(recipient=self.me, kind="friend_accept").exists())
        self.assertFalse(Notification.objects.filter(kind="friend_request").exists())

    def test_unknown_username_and_self(self):
        r = self.client.post(reverse("social:friend_add"), {"username": "nobody"}, follow=True)
        self.assertContains(r, "لا يوجد مستخدم")
        self.client.post(reverse("social:friend_add"), {"username": "me"})
        self.assertEqual(Friendship.objects.count(), 0)

    def test_mutual_request_auto_accepts(self):
        Friendship.objects.create(requester=self.ann, addressee=self.me)
        self.client.post(reverse("social:friend_add"), {"username": "ann"})
        self.assertEqual(Friendship.objects.get().status, "accepted")

    def test_only_addressee_can_accept_and_decline_removes(self):
        f = Friendship.objects.create(requester=self.me, addressee=self.ann)
        self.assertEqual(self.client.post(reverse("social:friend_respond", args=[f.pk, "accept"])).status_code, 404)
        stranger = make_user("zed")
        self.client.force_login(stranger)
        self.assertEqual(self.client.post(reverse("social:friend_respond", args=[f.pk, "decline"])).status_code, 404)
        self.client.force_login(self.ann)
        self.client.post(reverse("social:friend_respond", args=[f.pk, "decline"]))
        self.assertEqual(Friendship.objects.count(), 0)

    def test_profile_shows_friend_button(self):
        r = self.client.get(reverse("feed:profile", args=["ann"]))
        self.assertContains(r, "إضافة صديق")


class MessageTests(TestCase):
    def setUp(self):
        self.me = make_user("me")
        self.ann = make_user("ann")
        self.zed = make_user("zed")
        Friendship.objects.create(requester=self.me, addressee=self.ann, status="accepted")
        self.client.force_login(self.me)

    def test_send_and_read(self):
        r = self.client.post(reverse("social:send", args=["ann"]), {"body": "  hello  "}, HTTP_HX_REQUEST="true")
        self.assertContains(r, "hello")
        m = Message.objects.get()
        self.assertEqual((m.sender, m.recipient, m.body), (self.me, self.ann, "hello"))
        self.assertIsNone(m.read_at)
        self.client.force_login(self.ann)
        self.assertContains(self.client.get(reverse("social:inbox")), "hello")
        self.client.get(reverse("social:thread", args=["me"]))
        m.refresh_from_db()
        self.assertIsNotNone(m.read_at)

    def test_only_friends_can_message(self):
        self.assertEqual(self.client.get(reverse("social:thread", args=["zed"])).status_code, 404)
        self.assertEqual(self.client.post(reverse("social:send", args=["zed"]), {"body": "hi"}).status_code, 404)
        self.assertEqual(Message.objects.count(), 0)

    def test_empty_and_long_bodies(self):
        self.client.post(reverse("social:send", args=["ann"]), {"body": "   "})
        self.assertEqual(Message.objects.count(), 0)
        self.client.post(reverse("social:send", args=["ann"]), {"body": "x" * 5000})
        self.assertEqual(len(Message.objects.get().body), 1000)

    def test_poll_returns_only_new_messages_from_other(self):
        a = Message.objects.create(sender=self.ann, recipient=self.me, body="one")
        Message.objects.create(sender=self.me, recipient=self.ann, body="mine")
        r = self.client.get(reverse("social:poll", args=["ann"]) + f"?after={a.id - 1}")
        self.assertContains(r, "one")
        self.assertNotContains(r, "mine")
        again = self.client.get(reverse("social:poll", args=["ann"]) + f"?after={a.id}")
        self.assertNotContains(again, "one")

    def test_third_party_cannot_read(self):
        Message.objects.create(sender=self.ann, recipient=self.me, body="secret text")
        self.client.force_login(self.zed)
        self.assertEqual(self.client.get(reverse("social:thread", args=["ann"])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("social:inbox")), "secret text")

    def test_unread_badge_counts(self):
        Message.objects.create(sender=self.ann, recipient=self.me, body="hi")
        r = self.client.get(reverse("feed:home"))
        self.assertEqual(r.context["unread_messages_count"], 1)
