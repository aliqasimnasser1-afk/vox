FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# ffmpeg powers the video splitter
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces run the container as user 1000, so the app must live in a directory that user owns.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
COPY --chown=user . .

# DEBUG off, random per-boot secret (set SECRET_KEY as a Space secret to keep sessions across restarts),
# uploads in the database, and the port Spaces expect.
ENV DEBUG=0 ALLOW_EPHEMERAL_SECRET=1 MEDIA_IN_DB=1 PORT=7860
RUN SECRET_KEY=build-only DEBUG=1 python manage.py collectstatic --noinput

# One worker with threads: the video splitter tracks running jobs in process memory.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 300"]
