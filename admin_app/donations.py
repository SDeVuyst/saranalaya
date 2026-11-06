import json
import math
from dataclasses import dataclass, field
from datetime import date

from django import forms
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from .models import Donation, Sponsor
from .payments import AmountError, format_amount


class DonationError(Exception):
    pass


@dataclass
class SponsorChoice:
    pk: int
    name: str


@dataclass
class SponsorFilters:
    name: str


@dataclass
class DonationItem:
    pk: int
    amount: str
    date: str
    date_label: str
    description: str
    change_url: str
    amount_url: str


@dataclass
class DonationCell:
    year: int
    donations: list = field(default_factory=list)
    total: float | None = None
    total_label: str = ""
    default_date: str = ""


@dataclass
class SponsorRow:
    pk: int
    name: str
    url: str
    badges: list
    cells: list


@dataclass
class YearTotal:
    year: int
    total: float | None
    label: str


@dataclass
class DonationGrid:
    year: int
    years: list
    rows: list
    totals: list
    filters: SponsorFilters
    sponsor_choices: list
    today: str


class SponsorQuickForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = [
            "first_name",
            "last_name",
            "firm",
            "mail",
            "phone_number",
            "street_name",
            "address_number",
            "bus",
            "postcode",
            "city",
            "country",
            "letters",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["letters"].required = False
        self.fields["country"].initial = "Belgium"


def request_payload(request):
    content_type = request.content_type or ""
    if "application/json" in content_type:
        try:
            data = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    return request.POST


def form_error(form):
    parts = []
    for name, errors in form.errors.items():
        if name == "__all__" or name not in form.fields:
            parts.extend(str(error) for error in errors)
            continue
        parts.append(f"{form.fields[name].label}: {errors[0]}")
    return " ".join(parts) or _("Could not save this sponsor.")


def build_donation_grid(*, name="", year=None, today=None):
    today = date.today() if today is None else today
    year = today.year if year is None else year
    sponsors = list(Sponsor.objects.all().order_by("first_name", "last_name", "pk"))
    donations = list(Donation.objects.order_by("date", "pk"))
    filters = SponsorFilters(name=(name or "").strip())
    years = _year_columns(donations, year)
    by_sponsor = {}
    for donation in donations:
        by_sponsor.setdefault(donation.sponsor_id, []).append(donation)

    rows = []
    for sponsor in sponsors:
        if not _matches(sponsor, filters.name):
            continue
        owned = by_sponsor.get(sponsor.pk, [])
        rows.append(SponsorRow(
            pk=sponsor.pk,
            name=str(sponsor),
            url=reverse("admin:admin_app_sponsor_change", args=[sponsor.pk]),
            badges=_badges(sponsor),
            cells=[_cell(owned, item, today) for item in years],
        ))
    return DonationGrid(
        year=year,
        years=years,
        rows=rows,
        totals=_totals(rows, years),
        filters=filters,
        sponsor_choices=[SponsorChoice(pk=sponsor.pk, name=str(sponsor)) for sponsor in sponsors],
        today=today.isoformat(),
    )


def visible_sponsor_ids(name=""):
    return [row.pk for row in build_donation_grid(name=name).rows]


def new_donation(sponsor_id, raw_amount, raw_date, description=""):
    try:
        sponsor = Sponsor.objects.get(pk=sponsor_id)
    except (TypeError, ValueError, Sponsor.DoesNotExist):
        raise DonationError(_("That sponsor could not be found."))
    donation = Donation(sponsor=sponsor)
    apply_donation_fields(donation, raw_amount, raw_date, description)
    return donation


def update_donation(donation, raw_amount, raw_date, description):
    apply_donation_fields(donation, raw_amount, raw_date, description)
    donation.save()
    return donation_payload(donation)


def donation_payload(donation):
    return {
        "pk": donation.pk,
        "amount": format_amount(donation.amount),
        "date": donation.date.isoformat(),
        "date_label": _date_label(donation.date),
        "year": donation.date.year,
        "description": donation.description or "",
        "change_url": reverse("admin:admin_app_donation_change", args=[donation.pk]),
        "amount_url": reverse("admin:sponsor_donation_amount", args=[donation.pk]),
    }


def apply_donation_fields(donation, raw_amount, raw_date, description):
    donation.amount = _parse_amount(raw_amount)
    donation.date = _parse_date(raw_date)
    donation.description = (description or "").strip()


def _parse_amount(raw):
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        raise AmountError(_("Enter a number."))
    if math.isnan(amount) or math.isinf(amount) or amount < 0:
        raise AmountError(_("Amount cannot be negative."))
    return amount


def _parse_date(raw):
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        raise DonationError(_("Enter a valid date."))


def _matches(sponsor, name):
    if not name:
        return True
    haystack = " ".join([
        sponsor.first_name or "",
        sponsor.last_name or "",
        sponsor.firm or "",
    ]).lower()
    return name.lower() in haystack


def _badges(sponsor):
    badges = []
    if sponsor.firm:
        badges.append(sponsor.firm)
    if not sponsor.letters:
        badges.append(str(_lazy("No letters")))
    return badges


def _year_columns(donations, current_year):
    years = {current_year}
    for donation in donations:
        years.add(donation.date.year)
    others = sorted((item for item in years if item != current_year), reverse=True)
    return [current_year, *others]


def _cell(donations, year, today):
    chosen = [donation for donation in donations if donation.date.year == year]
    total = sum(donation.amount for donation in chosen) if chosen else None
    if year == today.year:
        default_date = today
    else:
        default_date = date(year, 1, 1)
    return DonationCell(
        year=year,
        donations=[_item(donation) for donation in chosen],
        total=total,
        total_label="" if total is None else format_amount(total),
        default_date=default_date.isoformat(),
    )


def _item(donation):
    shown = donation_payload(donation)
    return DonationItem(
        pk=shown["pk"],
        amount=shown["amount"],
        date=shown["date"],
        date_label=shown["date_label"],
        description=shown["description"],
        change_url=shown["change_url"],
        amount_url=shown["amount_url"],
    )


def _totals(rows, years):
    totals = []
    for index, year in enumerate(years):
        amounts = []
        for row in rows:
            for donation in row.cells[index].donations:
                amounts.append(round(float(donation.amount) * 100))
        if not amounts:
            totals.append(YearTotal(year=year, total=None, label=""))
        else:
            total = sum(amounts) / 100
            totals.append(YearTotal(year=year, total=total, label=format_amount(total)))
    return totals


def _date_label(value):
    return f"{value.day}/{value.month}"
