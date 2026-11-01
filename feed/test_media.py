import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Post

User = get_user_model()
PW = "S3cure-test-pass!"
MEDIA = tempfile.mkdtemp(prefix="vox-media-test-")


def png_bytes(size=(40, 30), color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class PostMediaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user("p1", "p1@test.dev", PW, first_name="P")
        self.client.force_login(self.user)
        self.url = reverse("feed:post_create")

    def test_image_post_is_processed_and_served(self):
        self.client.post(self.url, {"content": "pic", "media": SimpleUploadedFile("a.png", png_bytes(), content_type="image/png")})
        post = Post.objects.get()
        self.assertTrue(post.image and not post.video)
        r = self.client.get(post.image.url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("image/"))

    def test_large_image_is_downscaled_and_exif_dropped(self):
        buf = io.BytesIO()
        Image.new("RGB", (4000, 3000), (10, 120, 200)).save(buf, "JPEG")
        self.client.post(self.url, {"media": SimpleUploadedFile("big.jpg", buf.getvalue(), content_type="image/jpeg")})
        post = Post.objects.get()
        self.assertEqual(post.content, "")  # media alone is a valid post
        with Image.open(post.image.path) as im:
            self.assertLessEqual(max(im.size), 1600)

    def test_fake_image_and_bad_type_rejected(self):
        self.client.post(self.url, {"media": SimpleUploadedFile("evil.png", b"not really a png")})
        self.client.post(self.url, {"media": SimpleUploadedFile("run.exe", b"MZ....")})
        self.assertEqual(Post.objects.count(), 0)

    def test_video_post_and_delete_removes_file(self):
        self.client.post(self.url, {"content": "clip", "media": SimpleUploadedFile("c.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 64, content_type="video/mp4")})
        post = Post.objects.get()
        self.assertTrue(post.video and not post.image)
        path = post.video.path
        self.assertTrue(self.client.get(post.video.url).status_code == 200)
        self.client.post(reverse("feed:delete", args=[post.id]))
        import os
        self.assertFalse(os.path.exists(path))

    def test_empty_post_rejected(self):
        self.client.post(self.url, {"content": "   "})
        self.assertEqual(Post.objects.count(), 0)

    def test_splitter_files_never_served_from_media(self):
        self.assertEqual(self.client.get("/media/splitter/parts/1/part_001.mp4").status_code, 404)
        self.assertEqual(self.client.get("/media/../manage.py").status_code, 404)


class PrivacyTests(TestCase):
    def test_email_never_rendered_and_username_chosen(self):
        u = User.objects.create_user("shown_handle", "secret.person@example-mail.com", PW, first_name="Sam")
        self.client.force_login(u)
        for url in ("/", "/u/shown_handle/", "/friends/", "/messages/", "/notifications/", "/settings/profile/"):
            body = self.client.get(url).content.decode()
            self.assertNotIn("secret.person", body, url)
            self.assertNotIn("example-mail.com", body, url)

    def test_username_rules(self):
        from accounts.validators import clean_username
        from django.core.exceptions import ValidationError
        User.objects.create_user("taken_name", "t@test.dev", PW)
        for bad in ("ab", "UPPER space", "x" * 21, "admin", "taken_name", "عربي"):
            with self.assertRaises(ValidationError, msg=bad):
                clean_username(bad)
        self.assertEqual(clean_username("@New_Name1"), "new_name1")

    def test_profile_edit_can_change_username(self):
        u = User.objects.create_user("old_name", "o@test.dev", PW, first_name="O")
        self.client.force_login(u)
        r = self.client.post("/settings/profile/", {"display_name": "O", "username": "fresh_name", "bio": "", "location": "", "website": ""})
        self.assertEqual(r.status_code, 302)
        u.refresh_from_db()
        self.assertEqual(u.username, "fresh_name")


class UiMarkupTests(TestCase):
    """The site must use its own dialogs and lightbox, never the browser's confirm()."""

    def setUp(self):
        self.user = User.objects.create_user("ui1", "ui1@test.dev", PW, first_name="U")
        self.client.force_login(self.user)

    def test_no_native_confirm_anywhere(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent / "templates"
        for f in root.rglob("*.html"):
            self.assertNotIn("confirm(", f.read_text(encoding="utf-8"), str(f))

    def test_dialogs_present_and_delete_is_styled(self):
        Post.objects.create(author=self.user, content="x")
        html = self.client.get("/").content.decode()
        self.assertIn('id="confirm-dialog"', html)
        self.assertIn('id="lightbox"', html)
        self.assertIn("data-confirm-title", html)  # delete button carries the dialog text
        self.assertIn("media-ui.js", html)

    def test_media_posts_are_lightbox_enabled(self):
        import shutil
        from django.test import override_settings
        tmp = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=tmp):
            img = SimpleUploadedFile("a.png", png_bytes(), content_type="image/png")
            self.client.post(reverse("feed:post_create"), {"content": "pic", "media": img})
            self.client.post(reverse("feed:post_create"), {"content": "vid", "media": SimpleUploadedFile("c.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 64, content_type="video/mp4")})
            html = self.client.get("/").content.decode()
        shutil.rmtree(tmp, ignore_errors=True)
        self.assertIn('data-lightbox="image"', html)
        self.assertIn('data-lightbox="video"', html)
