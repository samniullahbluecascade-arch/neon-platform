.PHONY: dev migrate superuser worker beat shell test docker-up docker-down

# ── Local dev (SQLite, no Docker) ─────────────────────────────────────────────
dev:
	DJANGO_SETTINGS_MODULE=neon_platform.settings.development \
	python manage.py runserver 0.0.0.0:8000

migrate:
	DJANGO_SETTINGS_MODULE=neon_platform.settings.development \
	python manage.py migrate

superuser:
	DJANGO_SETTINGS_MODULE=neon_platform.settings.development \
	python manage.py createsuperuser

worker:
	DJANGO_SETTINGS_MODULE=neon_platform.settings.development \
	celery -A neon_platform worker --loglevel=debug --concurrency=1

beat:
	DJANGO_SETTINGS_MODULE=neon_platform.settings.development \
	celery -A neon_platform beat --loglevel=info

shell:
	DJANGO_SETTINGS_MODULE=neon_platform.settings.development \
	python manage.py shell_plus

test:
	DJANGO_SETTINGS_MODULE=neon_platform.settings.development \
	python manage.py test --verbosity=2

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

# ── Stripe CLI (forward webhooks in dev) ──────────────────────────────────────
stripe-listen:
	stripe listen --forward-to localhost:8000/api/stripe/webhook/
