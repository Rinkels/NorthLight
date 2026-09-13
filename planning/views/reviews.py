"""Monthly / quarterly / annual / life reviews."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..access import get_owned_or_404, owned
from ..forms import ReviewForm, ScoreFormSet
from ..models import LifeAreaAssessment, PersonalYear, Review, ReviewType
from ..services import save_changed_scores, current_year, ensure_assessments, start_vs_end

SCORE_REVIEWS = (ReviewType.MONTHLY, ReviewType.QUARTERLY, ReviewType.ANNUAL, ReviewType.LIFE)


def _default_label(kind: str, year: PersonalYear, today) -> str:
    if kind == ReviewType.MONTHLY:
        return today.strftime("%B %Y")
    if kind == ReviewType.QUARTERLY:
        q = year.quarter_for(today)
        return f"Q{q}" if q else today.strftime("%B %Y")
    if kind == ReviewType.ANNUAL:
        return year.title
    return f"Life Review {today.year}"


@login_required
def review_list(request):
    reviews = owned(Review, request.user).select_related("personal_year")
    return render(request, "planning/review_list.html", {"reviews": reviews, "types": ReviewType.choices,
                                                          "year": current_year(request.user)})


@login_required
def review_create(request, kind):
    if kind not in ReviewType.values:
        raise Http404
    year = current_year(request.user)
    if year is None:
        messages.warning(request, "Create a Personal Year first.")
        return redirect("planning:year_create")
    ensure_assessments(year)
    today = timezone.localdate()
    form = ReviewForm(request.POST or None, review_type=kind,
                      initial={"review_date": today, "period_label": _default_label(kind, year, today)})
    scores = ScoreFormSet(request.POST or None, prefix="scores",
                          queryset=LifeAreaAssessment.objects.filter(personal_year=year).select_related("life_area"))
    if request.method == "POST" and form.is_valid() and scores.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.personal_year = year
        review.review_type = kind
        review.save()
        save_changed_scores(scores, year, source=f"{kind} review")
        messages.success(request, f"{review.get_review_type_display()} saved.")
        return redirect("planning:review_detail", pk=review.pk)
    return render(request, "planning/review_form.html", {
        "form": form, "scores": scores, "kind": kind, "year": year,
        "kind_label": ReviewType(kind).label,
        "comparison": start_vs_end(year) if kind == ReviewType.ANNUAL else None,
    })


@login_required
def review_detail(request, pk):
    review = get_owned_or_404(Review, request.user, pk=pk)
    return render(request, "planning/review_detail.html", {"review": review})


@login_required
def review_edit(request, pk):
    review = get_owned_or_404(Review, request.user, pk=pk)
    form = ReviewForm(request.POST or None, instance=review, review_type=review.review_type)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Review updated.")
        return redirect("planning:review_detail", pk=review.pk)
    return render(request, "planning/review_form.html", {
        "form": form, "scores": None, "kind": review.review_type, "year": review.personal_year,
        "kind_label": review.get_review_type_display(), "review": review, "comparison": None,
    })


@login_required
@require_POST
def review_delete(request, pk):
    review = get_owned_or_404(Review, request.user, pk=pk)
    review.delete()
    return redirect("planning:review_list")
