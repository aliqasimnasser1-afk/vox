"""WSGI file for PythonAnywhere: paste this whole file into the Web tab's WSGI configuration file.

Replace USERNAME with your PythonAnywhere username (and DOMAIN if you use a custom one).
No secrets go here: the Django secret key is read from /home/USERNAME/vox/.secret_key.
"""
import os
import sys

USERNAME = "ALIQASIM"
DOMAIN = f"{USERNAME.lower()}.pythonanywhere.com"
PROJECT = f"/home/{USERNAME}/vox"

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DEBUG"] = "0"
os.environ["MEDIA_IN_DB"] = "1"          # uploads live in the database (PythonAnywhere's disk is small)
os.environ["PYTHONANYWHERE_DOMAIN"] = DOMAIN
# Free accounts have 512 MB of disk (source + parts) and a 100 MB per-request proxy limit (chunked upload handles that).
os.environ["MAX_VIDEO_MB"] = "150"

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
