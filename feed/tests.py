from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Bookmark, Follow, Like, Notification, Post

User = get_user_model()
PW = "S3cure-test-pass!"


def make_user(name, email=None):
    return User.objects.create_user(username=name, email=email or f"{name}@test.dev", password=PW, first_name=name)


class AuthTests(TestCase):
    def test_signup_logs_in_and_creates_profile(self):
        r = self.client.post(reverse("accounts:signup"), {"name": "Ali", "email": "Ali@Test.dev", "password": PW})
        self.assertRedirects(r, reverse("feed:home"))
        u = User.objects.get(email="ali@test.dev")
        self.assertEqual(u.profile.display_name, "Ali")

    def test_signup_rejects_duplicate_email_and_weak_password(self):
        make_user("bob")
        r = self.client.post(reverse("accounts:signup"), {"name": "Bob2", "email": "BOB@test.dev", "password": PW})
        self.assertContains(r, "مسجّل مسبقاً")
        r = self.client.post(reverse("accounts:signup"), {"name": "Zed", "email": "z@test.dev", "password": "12345678"})
        self.assertEqual(User.objects.filter(email="z@test.dev").count(), 0)

    def test_login_by_email(self):
        make_user("carl")
        r = self.client.post(reverse("accounts:login"), {"email": "CARL@test.dev", "password": PW})
        self.assertRedirects(r, reverse("feed:home"))
        self.client.logout()
        bad = self.client.post(reverse("accounts:login"), {"email": "carl@test.dev", "password": "nope"})
        self.assertContains(bad, "غير صحيحة")

    def test_home_requires_login(self):
        r = self.client.get(reverse("feed:home"))
        self.assertEqual(r.status_code, 302)


class PostTests(TestCase):
    def setUp(self):
        self.me = make_user("me")
        self.other = make_user("other")
        self.client.force_login(self.me)

    def test_create_post_and_limit(self):
        self.client.post(reverse("feed:post_create"), {"content": "hello"})
        self.assertEqual(Post.objects.count(), 1)
        self.client.post(reverse("feed:post_create"), {"content": "x" * 281})
        self.client.post(reverse("feed:post_create"), {"content": "   "})
        self.assertEqual(Post.objects.count(), 1)

    def test_like_toggle(self):
        p = Post.objects.create(author=self.other, content="hi")
        url = reverse("feed:like", args=[p.id])
        self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(Like.objects.count(), 1)
        self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(Like.objects.count(), 0)

    def test_only_author_can_delete(self):
        p = Post.objects.create(author=self.other, content="hi")
        r = self.client.post(reverse("feed:delete", args=[p.id]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=p.pk).exists())
        mine = Post.objects.create(author=self.me, content="mine")
        self.client.post(reverse("feed:delete", args=[mine.id]))
        self.assertFalse(Post.objects.filter(pk=mine.pk).exists())

    def test_follow_and_following_feed(self):
        Post.objects.create(author=self.other, content="from other")
        r = self.client.get(reverse("feed:home") + "?tab=following")
        self.assertNotContains(r, "from other")
        self.client.post(reverse("feed:follow", args=["other"]))
        self.assertEqual(Follow.objects.count(), 1)
        r = self.client.get(reverse("feed:home") + "?tab=following")
        self.assertContains(r, "from other")
        self.client.post(reverse("feed:follow", args=["me"]))  # cannot follow self
        self.assertEqual(Follow.objects.count(), 1)

    def test_profile_page(self):
        r = self.client.get(reverse("feed:profile", args=["other"]))
        self.assertContains(r, "@other")


class NotificationTests(TestCase):
    def setUp(self):
        self.me = make_user("me")
        self.other = make_user("other")
        self.post = Post.objects.create(author=self.me, content="my post")

    def test_like_notifies_author_and_unlike_removes(self):
        self.client.force_login(self.other)
        url = reverse("feed:like", args=[self.post.id])
        self.client.post(url)
        self.assertEqual(Notification.objects.filter(recipient=self.me, kind="like").count(), 1)
        self.client.post(url)
        self.assertEqual(Notification.objects.count(), 0)

    def test_self_like_does_not_notify(self):
        self.client.force_login(self.me)
        self.client.post(reverse("feed:like", args=[self.post.id]))
        self.assertEqual(Notification.objects.count(), 0)

    def test_follow_notifies(self):
        self.client.force_login(self.other)
        self.client.post(reverse("feed:follow", args=["me"]))
        n = Notification.objects.get()
        self.assertEqual((n.recipient, n.actor, n.kind), (self.me, self.other, "follow"))

    def test_page_marks_read_and_badge_counts(self):
        Notification.objects.create(recipient=self.me, actor=self.other, kind="follow")
        self.client.force_login(self.me)
        self.assertContains(self.client.get(reverse("feed:badge")), "badge")
        r = self.client.get(reverse("feed:notifications"))
        self.assertContains(r, "بدأ بمتابعتك")
        self.assertFalse(Notification.objects.filter(is_read=False).exists())
        self.assertNotContains(self.client.get(reverse("feed:badge")), 'class="badge"')

    def test_notifications_are_private(self):
        Notification.objects.create(recipient=self.me, actor=self.other, kind="follow")
        self.client.force_login(self.other)
        r = self.client.get(reverse("feed:notifications"))
        self.assertNotContains(r, "بدأ بمتابعتك")


class BookmarkTests(TestCase):
    def setUp(self):
        self.me = make_user("me")
        self.other = make_user("other")
        self.post = Post.objects.create(author=self.other, content="save me")
        self.client.force_login(self.me)

    def test_toggle_and_list(self):
        url = reverse("feed:bookmark", args=[self.post.id])
        self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertContains(self.client.get(reverse("feed:bookmarks")), "save me")
        r = self.client.post(url, HTTP_HX_REQUEST="true", HTTP_HX_CURRENT_URL="http://x/bookmarks/")
        self.assertEqual(Bookmark.objects.count(), 0)
        self.assertEqual(r.content, b"")

    def test_bookmarks_are_per_user(self):
        Bookmark.objects.create(user=self.other, post=self.post)
        self.assertNotContains(self.client.get(reverse("feed:bookmarks")), "save me")


class ProfileTests(TestCase):
    def setUp(self):
        self.me = make_user("me")
        self.client.force_login(self.me)

    def test_edit_profile_fields(self):
        r = self.client.post(reverse("accounts:profile_edit"), {
            "display_name": "Ali N", "bio": "hi", "location": "Riyadh", "website": "https://example.com",
        })
        self.assertRedirects(r, reverse("feed:profile", args=["me"]))
        p = self.me.profile
        p.refresh_from_db()
        self.assertEqual((p.display_name, p.location, p.website), ("Ali N", "Riyadh", "https://example.com"))

    def test_likes_tab_and_follow_lists(self):
        other = make_user("other")
        post = Post.objects.create(author=other, content="liked one")
        Like.objects.create(user=self.me, post=post)
        self.assertContains(self.client.get(reverse("feed:profile", args=["me"]) + "?tab=likes"), "liked one")
        Follow.objects.create(follower=self.me, followee=other)
        self.assertContains(self.client.get(reverse("feed:follow_list", args=["me", "following"])), "@other")
        self.assertContains(self.client.get(reverse("feed:follow_list", args=["other", "followers"])), "@me")

    def test_post_detail(self):
        post = Post.objects.create(author=self.me, content="detail text")
        self.assertContains(self.client.get(reverse("feed:post_detail", args=[post.id])), "detail text")
