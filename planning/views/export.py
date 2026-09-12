"""Data export: a page explaining the formats, plus the downloads themselves."""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from ..export import export_user_data, goals_csv_rows, scores_csv_rows, to_csv


def _stamp() -> str:
    return timezone.localdate().isoformat()


def _attachment(content: str, filename: str, content_type: str) -> HttpResponse:
    resp = HttpResponse(content, content_type=f"{content_type}; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required
def export_page(request):
    return render(request, "planning/export.html")


@login_required
def export_json(request):
    data = export_user_data(request.user)
    return _attachment(json.dumps(data, indent=2, ensure_ascii=False),
                       f"northlight-export-{_stamp()}.json", "application/json")


@login_required
def export_scores_csv(request):
    return _attachment(to_csv(scores_csv_rows(request.user)), f"northlight-scores-{_stamp()}.csv", "text/csv")


@login_required
def export_goals_csv(request):
    return _attachment(to_csv(goals_csv_rows(request.user)), f"northlight-goals-{_stamp()}.csv", "text/csv")
