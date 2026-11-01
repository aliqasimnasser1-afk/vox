import json
import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from . import chunked, services
from .models import VideoJob
from .tests import make_video

User = get_user_model()
PW = "S3cure-test-pass!"
MEDIA = tempfile.mkdtemp(prefix="vox-chunk-test-")


@override_settings(MEDIA_ROOT=MEDIA)
class ChunkedUploadTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not services.tools_available():
            raise cls.skipTest(cls, "ffmpeg not installed")
        cls.video = make_video(8)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user("c1", "c1@test.dev", PW)
        self.client.force_login(self.user)

    def init(self, name="big.mp4", size=None):
        r = self.client.post(reverse("splitter:chunk_init"), {"name": name, "size": size if size is not None else len(self.video)})
        return r, (r.json() if r.status_code == 200 else None)

    def send_all(self, uid, size):
        pieces = [self.video[i:i + size] for i in range(0, len(self.video), size)]
        for i, piece in enumerate(pieces):
            r = self.client.post(reverse("splitter:chunk"), {"id": uid, "index": i, "chunk": SimpleUploadedFile("c", piece)})
            self.assertEqual(r.status_code, 200, r.content)
        return pieces

    def test_full_flow_assembles_and_splits(self):
        with mock.patch.object(chunked, "CHUNK_SIZE", 40_000):   # force several chunks from a small video
            r, meta = self.init()
            self.assertEqual(meta["chunks"], -(-len(self.video) // 40_000))
            self.assertGreater(meta["chunks"], 1)
            self.send_all(meta["id"], 40_000)
            with mock.patch.object(services, "start_job", side_effect=services.process_job):
                fin = self.client.post(reverse("splitter:chunk_finish"), {"id": meta["id"], "amount": 3, "unit": "s", "mode": "precise"})
        self.assertEqual(fin.status_code, 200, fin.content)
        job = VideoJob.objects.get()
        self.assertEqual(fin.json()["redirect"], reverse("splitter:detail", args=[job.pk]))
        self.assertEqual(job.status, VideoJob.DONE)
        self.assertEqual(job.parts.count(), 3)  # 8s / 3s -> 3+3+2
        with open(job.source.path, "rb") as f:
            self.assertEqual(f.read(), self.video)  # reassembled byte-for-byte
        self.assertFalse(list((chunked._tmp_root(self.user)).glob("*")))  # temp chunks removed

    def test_rejects_bad_name_size_and_limits(self):
        self.assertEqual(self.init("notes.txt")[0].status_code, 400)
        self.assertEqual(self.init(size=0)[0].status_code, 400)
        with mock.patch.object(chunked, "MAX_BYTES", 1000):
            r, _ = self.init()
            self.assertEqual(r.status_code, 400)
            self.assertIn("ميجابايت", r.json()["error"])

    def test_missing_chunks_unknown_and_foreign_sessions(self):
        with mock.patch.object(chunked, "CHUNK_SIZE", 40_000):
            _, meta = self.init()
            # only the first chunk sent
            self.client.post(reverse("splitter:chunk"), {"id": meta["id"], "index": 0, "chunk": SimpleUploadedFile("c", self.video[:40_000])})
            fin = self.client.post(reverse("splitter:chunk_finish"), {"id": meta["id"], "amount": 3, "unit": "s", "mode": "fast"})
            self.assertEqual(fin.status_code, 400)
            self.assertEqual(VideoJob.objects.count(), 0)
            # out-of-range index and a made-up id
            r = self.client.post(reverse("splitter:chunk"), {"id": meta["id"], "index": 999, "chunk": SimpleUploadedFile("c", b"x")})
            self.assertEqual(r.status_code, 400)
            r = self.client.post(reverse("splitter:chunk"), {"id": "0" * 32, "index": 0, "chunk": SimpleUploadedFile("c", b"x")})
            self.assertEqual(r.status_code, 404)
            r = self.client.post(reverse("splitter:chunk"), {"id": "../../etc", "index": 0, "chunk": SimpleUploadedFile("c", b"x")})
            self.assertEqual(r.status_code, 404)
            # another user cannot use or finish my upload session
            self.client.force_login(User.objects.create_user("c2", "c2@test.dev", PW))
            r = self.client.post(reverse("splitter:chunk"), {"id": meta["id"], "index": 0, "chunk": SimpleUploadedFile("c", b"x")})
            self.assertEqual(r.status_code, 404)

    def test_abort_cleans_up_and_login_required(self):
        _, meta = self.init()
        folder = chunked._tmp_root(self.user) / meta["id"]
        self.assertTrue(folder.exists())
        self.client.post(reverse("splitter:chunk_abort"), {"id": meta["id"]})
        self.assertFalse(folder.exists())
        self.client.logout()
        self.assertEqual(self.client.post(reverse("splitter:chunk_init"), {"name": "a.mp4", "size": 10}).status_code, 302)

    def test_not_a_video_and_too_many_parts(self):
        with mock.patch.object(chunked, "CHUNK_SIZE", 100):
            r = self.client.post(reverse("splitter:chunk_init"), {"name": "fake.mp4", "size": 150})
            uid = r.json()["id"]
            for i, piece in enumerate([b"a" * 100, b"b" * 50]):
                self.client.post(reverse("splitter:chunk"), {"id": uid, "index": i, "chunk": SimpleUploadedFile("c", piece)})
            fin = self.client.post(reverse("splitter:chunk_finish"), {"id": uid, "amount": 3, "unit": "s", "mode": "fast"})
            self.assertEqual(fin.status_code, 400)
            self.assertIn("تعذّرت قراءة", fin.json()["error"])
        with mock.patch.object(chunked, "CHUNK_SIZE", 40_000), mock.patch.object(chunked, "MAX_PARTS", 1):
            _, meta = self.init()
            self.send_all(meta["id"], 40_000)
            fin = self.client.post(reverse("splitter:chunk_finish"), {"id": meta["id"], "amount": 3, "unit": "s", "mode": "fast"})
            self.assertEqual(fin.status_code, 400)
            self.assertIn("عدد الأجزاء", fin.json()["error"])
        self.assertEqual(VideoJob.objects.count(), 0)

    def test_page_exposes_chunk_endpoints_and_limit(self):
        html = self.client.get(reverse("splitter:index")).content.decode()
        for attr in ("data-chunk-init", "data-chunk-url", "data-chunk-finish", "chunked.js"):
            self.assertIn(attr, html)
        self.assertIn("ميجابايت", html)
