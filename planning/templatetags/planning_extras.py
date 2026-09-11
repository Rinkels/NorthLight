import os
from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static as static_url

register = template.Library()


@register.simple_tag
def static_v(path: str) -> str:
    """Static URL with the file's mtime as a cache-buster in DEBUG, so CSS edits
    show up without a hard refresh. Production should use
    ManifestStaticFilesStorage instead (hashed filenames)."""
    url = static_url(path)
    if settings.DEBUG:
        found = finders.find(path)
        if found:
            try:
                return f"{url}?v={int(os.path.getmtime(found))}"
            except OSError:
                pass
    return url

STATUS_CLASS = {
    "not_started": "secondary", "in_progress": "primary", "at_risk": "warning",
    "complete": "success", "paused": "light text-dark border", "dropped": "light text-muted border",
}
MODE_CLASS = {
    "improve": "primary", "protect": "success", "maintain": "secondary",
    "explore": "info", "deemphasize": "light text-muted border",
}


@register.filter
def is_checkbox(field) -> bool:
    return getattr(field.field.widget, "input_type", "") == "checkbox"


@register.filter
def status_class(value: str) -> str:
    return STATUS_CLASS.get(value, "secondary")


@register.filter
def mode_class(value: str) -> str:
    return MODE_CLASS.get(value, "secondary")


@register.filter
def gap_class(gap) -> str:
    """Priority gap is a signal, not a verdict — colour it gently."""
    if gap is None:
        return "text-muted"
    if gap >= 2:
        return "text-primary fw-semibold"
    if gap <= -2:
        return "text-success"
    return "text-body"


@register.filter
def signed(value) -> str:
    if value is None:
        return "—"
    return f"+{value}" if value > 0 else str(value)


CURRENCY_UNITS = {"$", "£", "€", "¥", "R", "USD", "CAD", "EUR", "GBP", "AUD", "ZAR"}


@register.filter
def num(value) -> str:
    """165000.00 → '165,000'; 27.50 → '27.5'; None → '—'."""
    if value is None or value == "":
        return "—"
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{d:,.2f}".rstrip("0").rstrip(".")


@register.simple_tag
def measure(value, unit: str = "") -> str:
    """Number + unit with sensible placement: '$165,000', 'CAD 165,000', '27.5 minutes'."""
    s = num(value)
    unit = (unit or "").strip()
    if not unit or s == "—":
        return s
    if unit in CURRENCY_UNITS or unit.upper() in CURRENCY_UNITS:
        return f"{unit}{s}" if len(unit) == 1 else f"{unit} {s}"
    return f"{s} {unit}"
