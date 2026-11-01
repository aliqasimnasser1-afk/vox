#!/bin/bash
# Set up Vox on PythonAnywhere. Run in a Bash console on your account:
#   bash <(curl -s https://raw.githubusercontent.com/aliqasimnasser1-afk/vox/main/deploy/pythonanywhere/setup.sh)
# or, if the repo is already cloned:  bash ~/vox/deploy/pythonanywhere/setup.sh
set -e

DOMAIN="${PA_DOMAIN:-$(whoami | tr 'A-Z' 'a-z').pythonanywhere.com}"
REPO="https://github.com/aliqasimnasser1-afk/vox.git"

cd ~
if [ -d vox/.git ]; then (cd vox && git pull --ff-only); else git clone "$REPO" vox; fi
cd vox

# Django 5 needs Python 3.10+. Pick the newest one available on this account.
PY=""
for v in 3.13 3.12 3.11 3.10; do
  if command -v python$v >/dev/null 2>&1; then PY=python$v; break; fi
done
[ -n "$PY" ] || { echo "No Python 3.10+ found"; exit 1; }
echo "Using $PY"

[ -d ~/venv-vox ] || $PY -m venv ~/venv-vox
source ~/venv-vox/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# A secret key generated once, on the server. It never leaves this account.
[ -f .secret_key ] || python -c "import secrets; print(secrets.token_urlsafe(64))" > .secret_key
chmod 600 .secret_key

export DEBUG=0 MEDIA_IN_DB=1 PYTHONANYWHERE_DOMAIN="$DOMAIN"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo
echo "ffmpeg: $(command -v ffmpeg || echo 'not found (video splitter will be disabled)')"
echo
echo "Setup finished for https://$DOMAIN"
echo "Now open the Web tab, point the app at /home/$(whoami)/vox and use the WSGI file from deploy/pythonanywhere/wsgi.py"
