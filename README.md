# Vox

A small X-style social app built with Django. Local development only.

**Features:** sign up and log in with email, 280-character posts, likes (HTMX, no page reload),
follow/unfollow with a "following" timeline, profiles, pagination, Django admin.

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
| `accounts/` | email login backend, signup, profile model and edit |
| `feed/` | posts, likes, follows, timeline and profile views |
| `templates/`, `static/` | RTL Arabic UI, HTMX for likes and deletes |
| `config/` | settings and root URLs |

## Notes

- `SECRET_KEY` in `config/settings.py` is a development placeholder. Set a real one and
  `DEBUG = False` before any deployment.
- The database is SQLite (`db.sqlite3`, git-ignored).
- Ideas for later: replies, hashtags and search, notifications, images, realtime updates
  (Django Channels).
