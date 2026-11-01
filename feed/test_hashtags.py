import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import hashtags
from .models import Bookmark, Hashtag, Post

User = get_user_model()
PW = "S3cure-test-pass!"


def make_user(name):
    return User.objects.create_user(username=name, email=f"{name}@test.dev", password=PW, first_name=name)


class HashtagParsingTests(TestCase):
    def test_extract(self):
        self.assertEqual(hashtags.extract("hello #Tech and #رياضة_اليوم #tech"), ["tech", "رياضة_اليوم"])
        self.assertEqual(hashtags.extract("#123 #__ # #a url.com/#frag x#nope"), [])  # digits-only, glued, too short
        self.assertEqual(len(hashtags.extract(" ".join(f"#tag{i}x" for i in range(30)))), hashtags.MAX_TAGS)

    def test_linkify_escapes_html(self):
        html = str(hashtags.linkify('<script>alert(1)</script> #ok &#x27; "quote"'))
        self.assertNotIn("<script>", html)
        self.assertIn('href="/tags/ok/"', html)
        self.assertNotIn("&#x27; #", html)  # entities are not mistaken for hashtags

    def test_arabic_tag_link(self):
        self.assertIn(">#رياضة</a>", str(hashtags.linkify("#رياضة")))


class HashtagFlowTests(TestCase):
    def setUp(self):
        self.me = make_user("me_user")
        self.client.force_login(self.me)

    def post(self, text):
        return self.client.post(reverse("feed:post_create"), {"content": text})

    def test_post_attaches_tags_and_tag_page_lists_it(self):
        r = self.post("أول تغريدة #رياضة و #Tech")
        self.assertRedirects(r, reverse("feed:home"))
        post = Post.objects.get()
        self.assertEqual(set(post.hashtags.values_list("name", flat=True)), {"رياضة", "tech"})
        page = self.client.get(reverse("feed:tag", args=["TECH"]))  # case-insensitive
        self.assertContains(page, "أول تغريدة")
        self.assertContains(page, "1 تغريدة")
        self.assertEqual(self.client.get(reverse("feed:tag", args=["nothing"])).status_code, 404)

    def test_deleting_post_removes_it_from_tag(self):
        self.post("bye #gone")
        Post.objects.get().delete()
        self.assertContains(self.client.get(reverse("feed:tag", args=["gone"])), "لا توجد تغريدات")

    def test_trending_orders_by_usage_and_ignores_old_posts(self):
        for text in ("a #alpha", "b #alpha", "c #alpha", "d #beta", "e #beta", "f #gamma"):
            self.post(text)
        old = Post.objects.create(author=self.me, content="old #ancient")
        Post.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=30))
        hashtags.attach(old)
        names = [(t.name, t.n) for t in hashtags.trending()]
        self.assertEqual(names[:3], [("alpha", 3), ("beta", 2), ("gamma", 1)])
        self.assertNotIn("ancient", [n for n, _ in names])

    def test_home_shows_posts_and_trending_but_no_composer(self):
        self.post("hello #home_tag")
        self.post("again #home_tag")
        self.post("third #home_tag")
        html = self.client.get(reverse("feed:home")).content.decode()
        self.assertIn("#home_tag", html)  # trending strip
        self.assertIn("الترند", html)
        self.assertNotIn('id="id_content"', html)  # composing lives on its own page
        self.assertIn(reverse("feed:post_create"), html)

    def test_compose_page(self):
        r = self.client.get(reverse("feed:post_create"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="id_content"')
        self.assertContains(r, 'enctype="multipart/form-data"')
        self.assertContains(self.post("   "), "اكتب شيئاً")  # invalid -> form re-rendered with an error
        self.assertEqual(Post.objects.count(), 0)

    def test_search(self):
        other = make_user("maria_k")
        Post.objects.create(author=other, content="learning django #python today")
        hashtags.attach(Post.objects.get())
        self.assertRedirects(self.client.get(reverse("feed:search"), {"q": "#python"}), reverse("feed:tag", args=["python"]))
        r = self.client.get(reverse("feed:search"), {"q": "django"})
        self.assertContains(r, "learning django")
        self.assertContains(self.client.get(reverse("feed:search"), {"q": "maria"}), "@maria_k")
        self.assertContains(self.client.get(reverse("feed:search"), {"q": "a"}), "حرفين على الأقل")

    def test_explore_lists_trend(self):
        self.post("x #hot_topic")
        self.assertContains(self.client.get(reverse("feed:explore")), "#hot_topic")


class ActionsKeepVideoPlayingTests(TestCase):
    """Like/save must swap only the action bar; re-rendering the post would restart (stop) a playing video."""

    def setUp(self):
        self.me = make_user("viewer")
        self.author = make_user("author_x")
        self.client.force_login(self.me)
        self.tmp = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=self.tmp):
            self.client.force_login(self.author)
            self.client.post(reverse("feed:post_create"), {
                "content": "clip", "media": SimpleUploadedFile("c.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 64, content_type="video/mp4")})
        self.client.force_login(self.me)
        self.post_obj = Post.objects.get()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_like_and_bookmark_return_only_actions(self):
        for name in ("feed:like", "feed:bookmark"):
            r = self.client.post(reverse(name, args=[self.post_obj.id]), HTTP_HX_REQUEST="true")
            body = r.content.decode()
            self.assertIn(f'id="actions-{self.post_obj.id}"', body)
            self.assertNotIn("<video", body)
            self.assertNotIn("<article", body)

    def test_buttons_target_actions_not_whole_post(self):
        with override_settings(MEDIA_ROOT=self.tmp):
            html = self.client.get(reverse("feed:home")).content.decode()
        self.assertIn(f'hx-target="#actions-{self.post_obj.id}"', html)

    def test_unsave_on_bookmarks_page_removes_whole_post(self):
        Bookmark.objects.create(user=self.me, post=self.post_obj)
        r = self.client.post(reverse("feed:bookmark", args=[self.post_obj.id]),
                             HTTP_HX_REQUEST="true", HTTP_HX_CURRENT_URL="http://x/bookmarks/")
        self.assertEqual(r.content, b"")
        self.assertEqual(r["HX-Retarget"], f"#post-{self.post_obj.id}")


class PrivateFavoritesTests(TestCase):
    def setUp(self):
        self.me = make_user("owner_u")
        self.other = make_user("nosy_u")
        post = Post.objects.create(author=self.other, content="secretly saved post")
        Bookmark.objects.create(user=self.me, post=post)

    def test_owner_sees_saved_tab(self):
        self.client.force_login(self.me)
        r = self.client.get(reverse("feed:profile", args=["owner_u"]) + "?tab=saved")
        self.assertContains(r, "secretly saved post")
        self.assertContains(r, "خاصة بك")

    def test_others_cannot_see_saved_tab_or_content(self):
        self.client.force_login(self.other)
        r = self.client.get(reverse("feed:profile", args=["owner_u"]) + "?tab=saved")
        self.assertNotContains(r, 'href="?tab=saved"')  # no tab link shown
        self.assertEqual(r.context["tab"], "posts")  # falls back, never leaks the list
        self.assertNotContains(r, "خاصة بك")
