# NorthLight on Cloud Run. Build with `gcloud run deploy --source .`.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Collect static with a throwaway key; the real key comes from Secret Manager at runtime.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=False python manage.py collectstatic --noinput

# Migrate on start (idempotent, fast at this scale), then serve.
CMD python manage.py migrate --noinput && \
    exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 60
