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

### Demo data

Loads the example profile from the product brief (ten scored areas, North
Lights, goals, 90-day milestones, habits, a review, and a previous year so
History has a trend). Development only — refuses to run unless `DEBUG=True`.

```bash
python manage.py load_demo            # user "demo", password "demo-northlight"
python manage.py load_demo --reset    # wipe that user's planning data first
```

## North Light starting points

Writing a North Light from a blank box is the hardest moment in onboarding, so
`planning/library.py` holds three sample (North Light, Why) pairs per default
area plus a general set for custom areas. The North Light form and onboarding
step 6 offer them under "Start from an example"; clicking one fills the fields
client-side (`static/js/northlight.js`) and the user edits from there. Nothing
is ever saved without the user choosing it.

## Design my life

A guided walk (`planning/views/design.py`), one active area per page, reached
from the dashboard or Life Areas. Each page offers the North Light samples and,
**only for areas marked Improve**, three sample goals from `GOAL_SAMPLES` in
`planning/library.py` with baseline and target deliberately blank. Protect,
Maintain, Explore and De-emphasize areas get no goal suggestions: not every
area needs a goal. Nothing is created unless the user ticks it, and the closing
page lists goals that still need a baseline and target.

## Paying attention

Goals must not become wishes in a database, so the dashboard asks questions
rather than issuing verdicts: a review-due prompt driven by the profile's
cadence (`services.next_review_due`), and a **Drifting** card listing open
goals untouched for six weeks and habits with no check-in for two
(`stale_goals`, `stale_habits`) with Update / Pause / Drop right there. The
Calendar page shows only dated things; habits are cadences and sit in a
week strip. No streaks, no scores.

## Data export

Settings → **Export your data**. The JSON export (`planning/export.py`) mirrors
the domain hierarchy and is lossless — profile, areas with North Lights, every
Personal Year with assessments and score snapshots, goals, milestones, habits
with check-ins, reviews. Two CSVs (scores per area per year, goals) cover the
spreadsheet cases. Every query is scoped through `owned()`, and tests assert
that one user's export never contains another's rows.

## Tests

```bash
python manage.py test planning
```

Covers cross-user isolation on GET **and** POST/update/delete paths, anonymous
access, the Priority Gap calculation, Personal Year date/active-year logic, goal
progress/status rules, ownership on create, onboarding, and a render smoke test
of every page.

## Routes

| Area | Routes |
| --- | --- |
| Auth | `/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/password_reset/…` |
| Core | `/` dashboard · `/scores/` (POST, update scores from the dashboard) · `/settings/` · `/history/` · `/onboarding/<1–9>/` |
| Calendar | `/calendar/` · `/calendar/<year>/<month>/` (milestones, goal target dates, reviews done and due, year bounds, Life Review; habits in a week strip) |
| Design my life | `/design/` · `/design/<n>/` (one active area per page) · `/design/done/` |
| Export | `/export/` · `/export/json/` (complete, lossless) · `/export/scores.csv` · `/export/goals.csv` |
| Export | `/export/` · `/export/json/` (complete, lossless) · `/export/scores.csv` · `/export/goals.csv` |
| Life Areas | `/areas/` · `/areas/<id>/` · `…/edit/` `…/archive/` `…/restore/` `…/north-light/` `…/assess/` · `/areas/reorder/` · `/areas/restore-defaults/` |
| Personal Years | `/years/` · `/years/new/` · `/years/<id>/` · `…/edit/` `…/activate/` `…/complete/` `…/archive/` `…/next/` |
| Goals | `/goals/` (filters: year, area, status, mode, type) · `/goals/new/` · `/goals/<id>/` · `…/edit/` `…/delete/` `…/status/` `…/link/` `…/unlink/<id>/` |
| Milestones | `/milestones/` (`?all=1` for every year) · `/goals/<id>/milestones/new/` · `/milestones/<id>/edit/` · `…/delete/` |
| Habits | `/habits/` · `/habits/new/` · `/habits/<id>/edit/` · `…/delete/` · `…/checkin/` |
| Reviews | `/reviews/` · `/reviews/new/<monthly|quarterly|annual|life>/` · `/reviews/<id>/` · `…/edit/` `…/delete/` |
| Admin | `/admin/` (support/dev only) |

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
