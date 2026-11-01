# Vox

A small X-style social app built with Django. Local development only.

**Features:** email sign-up and login, 280-character posts, likes and favorites (HTMX, no page reload),
notification center with a live unread badge (polls every 8s), follow/unfollow with a "following"
timeline and follower lists, full profiles (avatar upload, bio, location, website, posts and likes tabs),
post pages, who-to-follow suggestions, responsive layout (sidebar, right rail, mobile bottom nav),
video splitter (upload a video, choose a length in seconds or minutes, get equal parts with
progress, preview, per-part download and ZIP), pagination, Django admin.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/

Create an admin for `/admin/`:

```bash
python manage.py createsuperuser
```

Run the tests:

```bash
python manage.py test
```

## Layout

| Path | Purpose |
|------|---------|
| `accounts/` | email login backend, signup, profile model (avatar, bio, location, website) and edit |
| `feed/` | posts, likes, bookmarks, follows, notifications, timeline and profile views |
| `splitter/` | video splitter: ffmpeg worker thread, progress, parts, ZIP download |
| `templates/`, `static/` | RTL Arabic UI, HTMX for likes and deletes |
| `config/` | settings and root URLs |

## Notes

- The video splitter needs `ffmpeg` and `ffprobe` on the PATH. Splitting re-encodes (H.264/AAC) so every
  cut is exact; limits are 500 MB and 300 parts per video.
- `SECRET_KEY` in `config/settings.py` is a development placeholder. Set a real one and
  `DEBUG = False` before any deployment.
- The database is SQLite (`db.sqlite3`) and uploaded avatars go to `media/`; both are git-ignored.
- Ideas for later: replies, hashtags and search, images in posts, true realtime updates
  (Django Channels) instead of polling.

## Deploy (Render)

`render.yaml` is a Blueprint: a free Docker web service plus a free PostgreSQL database.
Render sets `DATABASE_URL`, generates `SECRET_KEY`, and the container runs migrations on start.

Live: https://vox-j4xf.onrender.com/

Free-tier limits: the service sleeps after ~15 minutes idle (first request takes ~50 s), the free
database expires after 30 days, and the disk is ephemeral, so uploaded avatars and split videos are
lost on restart or redeploy.
