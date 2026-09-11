# NorthLight

> Working product name — easy to change (see `PRODUCT_NAME` in settings).

A multi-user personal planning application built on an enhanced **Wheel of
Life**. It feels like a personal strategy dashboard, not a habit tracker: the
point is reflection and intentional direction, **not** making every area a 10.

The product repeatedly walks the user through this sequence — it is the core
intellectual property, and the app is built around it rather than around
generic task screens:

> Where am I? → What matters? → Where do I want to head? → Why? →
> What would I like to be true by the end of this Personal Year? →
> What measurable outcomes would demonstrate that? →
> What can I do in the next 90 days? → What should I **protect** rather than improve?

Core hierarchy: Life Area → Satisfaction → Importance → Priority Gap →
strategic mode → North Light → Why → 12-Month Vision → Goals → 90-Day
Milestones → Habits → Monthly / Quarterly / Annual Reviews, all framed by
user-defined **Personal Years**.

The full product brief lives in `docs/design/` once exported from Foundry/Athena.

## Stack

- Python · **Django 6+** · Django auth (registration, login, password reset)
- Bootstrap 5 (responsive) · **Chart.js** (Life Wheel radar, trends)
- **SQLite** for local dev; **PostgreSQL** in production via `DATABASE_URL`
  (models stay engine-agnostic — switching is config, not a redesign)

## Run locally

```bash
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -r requirements.txt
copy .env.example .env                              # then edit
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Non-negotiables

- **Per-user isolation.** Every query and object lookup enforces ownership
  server-side. Never rely on hiding links. Test GET *and* POST/update/delete
  paths for cross-user access.
- **Django security defaults.** Standard password hashing, CSRF, no secrets in
  the repo (`.env` is git-ignored). Don't log free-text personal reflections.
- **Calm UX.** Generous whitespace, subtle progress indicators. No streaks,
  points, confetti, or gamification. The North Light is visually distinctive.

## Future integrations (Phase 2 — not in V1)

NorthLight may later pull data to populate goal baselines / current values:

- **Health** from `gym2x` (fitness app)
- **Finance** from `fracto` (fund ledger / portfolio)

Do this **via API** with NorthLight as the client — never a shared database, so
the per-user isolation boundary stays intact. V1 keeps goal values manually
entered but routes updates through a thin service layer so a
`HealthProvider` / `FinanceProvider` can be added without touching the models.

## Project layout

```
config/        settings, root urls (auth under /accounts/)
planning/      the application (models, views, templates, tests)
templates/     base.html (Bootstrap + Chart.js), shared layouts
static/css/    northlight.css — extend here, avoid inline styles
docs/design/   product brief exported from Foundry/Athena
```
