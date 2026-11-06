import math
from dataclasses import dataclass, field
from datetime import date

from django.db import transaction
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from .models import (
    Adoption,
    AdoptionParent,
    AdoptionParentSponsoring,
    Child,
    StatusChoices,
    adoption_payment_target,
)

COLOR_UNPAID = "#dc2626"
COLOR_PARTIAL = "#facc15"
COLOR_PAID = "#16a34a"

AXIS_PARENTS = "parents"
AXIS_CHILDREN = "children"

LINK_ALL = "all"
LINK_ACTIVE = "active"
LINK_ENDED = "ended"

STANDING_DUE = "due"
STANDING_ANY = "any"
STANDING_MISSING = "missing"
STANDING_UNPAID = "unpaid"
STANDING_PARTIAL = "partial"
STANDING_PAID = "paid"

YEARLY_PAYMENT_TASK = "admin_app.tasks.add_yearly_adoption_parent_payments"

LINK_CHOICES = (
    (LINK_ALL, _lazy("All")),
    (LINK_ACTIVE, _lazy("Active only")),
    (LINK_ENDED, _lazy("Ended only")),
)

STANDING_CHOICES = (
    (STANDING_DUE, _lazy("Still to pay")),
    (STANDING_ANY, _lazy("Anyone")),
    (STANDING_PAID, _lazy("Paid in full")),
)

STANDING_VALUES = {
    STANDING_DUE,
    STANDING_ANY,
    STANDING_MISSING,
    STANDING_UNPAID,
    STANDING_PARTIAL,
    STANDING_PAID,
}


class AmountError(Exception):
    pass


class CreateError(Exception):
    pass


@dataclass
class CreateYearResult:
    year: int
    created: int
    already: int


@dataclass
class GridFilters:
    axis: str
    name: str
    link: str
    child_status: tuple
    standing: str


@dataclass
class GridPayment:
    pk: int
    amount: str
    color: str
    change_url: str
    amount_url: str
    has_description: bool = False


@dataclass
class GridCell:
    year: int
    kind: str
    payments: list = field(default_factory=list)
    marker: str = ""
    marker_kind: str = ""
    status: str = "closed"
    target: float = 0


@dataclass
class GridLeaf:
    name: str
    url: str
    ended: bool
    badges: list
    cells: list
    image_url: str = ""
    parent_id: int = 0
    child_id: int = 0


@dataclass
class YearSum:
    year: int
    total: float | None


@dataclass
class GridGroup:
    id: str
    name: str
    url: str
    ended: bool
    badges: list
    leaves: list
    sums: list
    image_url: str = ""


@dataclass
class PaymentGrid:
    axis: str
    year: int
    years: list
    groups: list
    filters: GridFilters
    target: float
    row_count: int = 0


@dataclass
class _Pair:
    parent: object
    child: object
    has_adoption: bool
    adoption_active: bool
    payments: list


def adoption_amount_target(year=None):
    if year is None:
        year = date.today().year
    return adoption_payment_target(year)


def amount_color(amount, target):
    standing = _amount_standing(amount, target)
    if standing == STANDING_PAID:
        return COLOR_PAID
    if standing == STANDING_PARTIAL:
        return COLOR_PARTIAL
    return COLOR_UNPAID


def format_amount(amount):
    cents = round(float(amount) * 100)
    if cents % 100 == 0:
        return str(cents // 100)
    return f"{cents / 100:.2f}"


def set_payment_amount(payment, raw):
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        raise AmountError(_("Enter a number."))
    if math.isnan(amount) or math.isinf(amount) or amount < 0:
        raise AmountError(_("Amount cannot be negative."))
    payment.amount = amount
    payment.save()
    return _payment_payload(payment, adoption_amount_target(payment.date.year))


def create_pair_payment(parent_id, child_id, year, raw_amount=None):
    try:
        year = int(year)
        parent = AdoptionParent.objects.get(pk=parent_id)
        child = Child.objects.get(pk=child_id)
    except (TypeError, ValueError, AdoptionParent.DoesNotExist, Child.DoesNotExist):
        raise CreateError(_("That adoption could not be found."))
    pair = _pair_for(parent, child)
    if not _expects_payment(pair, year):
        raise CreateError(_("This payment should not be created."))
    existing = _payments_in_year(pair, year)
    if existing:
        payment = existing[0]
    else:
        payment = AdoptionParentSponsoring.objects.create(
            date=date(year, 1, 1),
            amount=0,
            parent=parent,
            child=child,
        )
    if raw_amount is None or raw_amount == "":
        return _payment_payload(payment, adoption_amount_target(year))
    return set_payment_amount(payment, raw_amount)


def _payment_payload(payment, target):
    shown = _grid_payment(payment, target)
    return {
        "pk": payment.pk,
        "amount": shown.amount,
        "color": shown.color,
        "change_url": shown.change_url,
        "amount_url": shown.amount_url,
        "status": _amount_standing(payment.amount, target),
    }


def _amount_standing(amount, target):
    cents = round(float(amount) * 100)
    if cents == 0:
        return STANDING_UNPAID
    if cents < round(float(target) * 100):
        return STANDING_PARTIAL
    return STANDING_PAID


def _child_image_url(child):
    if child.image:
        return child.image.url
    return static("img/kinderen/kind_default.jpg")


def _pair_for(parent, child):
    adoptions = list(Adoption.objects.filter(adoptionparent=parent, child=child))
    payments = list(
        AdoptionParentSponsoring.objects.filter(parent=parent, child=child).order_by("date", "pk")
    )
    return _Pair(
        parent=parent,
        child=child,
        has_adoption=bool(adoptions),
        adoption_active=any(adoption.active for adoption in adoptions),
        payments=payments,
    )


def create_current_year_payments(year=None):
    year = date.today().year if year is None else year
    created = 0
    already = 0
    with transaction.atomic():
        for pair in _load_pairs():
            if not _expects_payment(pair, year):
                continue
            if _payments_in_year(pair, year):
                already += 1
                continue
            AdoptionParentSponsoring.objects.create(
                date=date(year, 1, 1),
                amount=0,
                parent=pair.parent,
                child=pair.child,
            )
            created += 1
    return CreateYearResult(year=year, created=created, already=already)


def build_payment_grid(
    *,
    axis=AXIS_PARENTS,
    name="",
    link=LINK_ALL,
    child_status="",
    standing=STANDING_ANY,
    year=None,
    today=None,
):
    year = date.today().year if year is None else year
    today = date.today() if today is None else today
    filters = GridFilters(
        axis=axis if axis in (AXIS_PARENTS, AXIS_CHILDREN) else AXIS_PARENTS,
        name=(name or "").strip(),
        link=link if link in (LINK_ALL, LINK_ACTIVE, LINK_ENDED) else LINK_ALL,
        child_status=_clean_statuses(child_status),
        standing=standing if standing in STANDING_VALUES else STANDING_ANY,
    )
    pairs = _load_pairs()
    years = _year_columns(pairs, year)
    target = adoption_amount_target(year)
    visible = [
        pair for pair in pairs
        if _pair_matches(pair, filters, year, target, today)
    ]
    groups = _group_pairs(visible, filters.axis, years, today)
    return PaymentGrid(
        axis=filters.axis,
        year=year,
        years=years,
        groups=groups,
        filters=filters,
        target=target,
        row_count=sum(len(group.leaves) for group in groups),
    )


def _load_pairs():
    grouped = {}
    adoptions = Adoption.objects.select_related("adoptionparent", "child")
    payments = AdoptionParentSponsoring.objects.select_related("parent", "child").order_by("date", "pk")

    for adoption in adoptions:
        pair = _bucket(grouped, adoption.adoptionparent, adoption.child)
        pair.has_adoption = True
        pair.adoption_active = pair.adoption_active or adoption.active

    for payment in payments:
        pair = _bucket(grouped, payment.parent, payment.child)
        pair.payments.append(payment)

    return list(grouped.values())


def _bucket(grouped, parent, child):
    key = (parent.pk, child.pk)
    pair = grouped.get(key)
    if pair is None:
        pair = _Pair(
            parent=parent,
            child=child,
            has_adoption=False,
            adoption_active=False,
            payments=[],
        )
        grouped[key] = pair
    return pair


def _expects_payment(pair, year):
    child = pair.child
    if not pair.has_adoption or not pair.adoption_active or not pair.parent.active:
        return False
    if child.status == StatusChoices.SUPPORT:
        return False
    if child.date_of_admission and child.date_of_admission > date(year, 12, 31):
        return False
    if child.date_of_leave and child.date_of_leave.year < year:
        return False
    if child.status == StatusChoices.LEFT:
        return bool(child.date_of_leave and child.date_of_leave.year == year)
    return child.status == StatusChoices.ACTIVE


def _payments_in_year(pair, year):
    return [payment for payment in pair.payments if payment.date.year == year]


def _link_inactive(pair):
    return (
        not pair.has_adoption
        or not pair.adoption_active
        or not pair.parent.active
    )


def _child_has_left(child, today):
    if child.status == StatusChoices.LEFT:
        return True
    return bool(child.date_of_leave and child.date_of_leave <= today)


def _is_ended(pair, today):
    return _link_inactive(pair) or _child_has_left(pair.child, today)


def _standing(pair, year, target=None):
    del target
    target = adoption_amount_target(year)
    amounts = [payment.amount for payment in _payments_in_year(pair, year)]
    if not amounts:
        return STANDING_MISSING if _expects_payment(pair, year) else "closed"
    total_cents = sum(round(float(amount) * 100) for amount in amounts)
    if total_cents == 0:
        return STANDING_UNPAID
    if total_cents >= round(float(target) * 100):
        return STANDING_PAID
    return STANDING_PARTIAL


def _pair_matches(pair, filters, year, target, today):
    if filters.name:
        haystack = " ".join([
            pair.parent.first_name,
            pair.parent.last_name,
            pair.child.name,
        ]).lower()
        if filters.name.lower() not in haystack:
            return False
    ended = _is_ended(pair, today)
    if filters.link == LINK_ACTIVE and ended:
        return False
    if filters.link == LINK_ENDED and not ended:
        return False
    if filters.child_status and pair.child.status not in filters.child_status:
        return False
    standing = _standing(pair, year, target)
    if filters.standing == STANDING_DUE:
        if not _expects_payment(pair, year) or standing == STANDING_PAID:
            return False
    elif filters.standing != STANDING_ANY and standing != filters.standing:
        return False
    return True


def _year_columns(pairs, current_year):
    years = {current_year}
    for pair in pairs:
        for payment in pair.payments:
            years.add(payment.date.year)
    others = sorted((item for item in years if item != current_year), reverse=True)
    return [current_year, *others]


def _cell(pair, year, target=None):
    del target
    target = adoption_amount_target(year)
    payments = _payments_in_year(pair, year)
    if payments:
        marker = ""
        marker_kind = ""
        leave = pair.child.date_of_leave
        if leave and year > leave.year:
            marker = _("After leave")
            marker_kind = "after_leave"
        elif _link_inactive(pair):
            marker = _("Ended")
            marker_kind = "ended"
        return GridCell(
            year=year,
            kind="payments",
            payments=[_grid_payment(payment, target) for payment in payments],
            marker=marker,
            marker_kind=marker_kind,
            status=_standing(pair, year, target),
            target=target,
        )
    if _expects_payment(pair, year):
        return GridCell(year=year, kind="missing", status=STANDING_MISSING, target=target)
    return GridCell(year=year, kind="closed", status="closed", target=target)


def _grid_payment(payment, target):
    return GridPayment(
        pk=payment.pk,
        amount=format_amount(payment.amount),
        color=amount_color(payment.amount, target),
        change_url=reverse("admin:admin_app_adoptionparentsponsoring_change", args=[payment.pk]),
        amount_url=reverse("admin:adoption_payment_amount", args=[payment.pk]),
        has_description=bool((payment.description or "").strip()),
    )


def _clean_statuses(child_status):
    if not child_status:
        return ()
    if isinstance(child_status, str):
        child_status = [child_status]
    return tuple(value for value in child_status if value in StatusChoices.values)


def _child_badges(child):
    if child.date_of_leave:
        return [_("Left %(year)s") % {"year": child.date_of_leave.year}]
    if child.status == StatusChoices.LEFT:
        return [_("Left, no leave date")]
    if child.status == StatusChoices.SUPPORT:
        return [_("Support")]
    return []


def _link_badges(pair):
    if not pair.has_adoption:
        return [_("No longer linked")]
    if not pair.adoption_active or not pair.parent.active:
        return [_("Inactive")]
    return []


def _group_pairs(pairs, axis, years, today):
    grouped = {}
    for pair in pairs:
        if axis == AXIS_CHILDREN:
            key = pair.child.pk
            header_name = str(pair.child)
            header_url = reverse("admin:admin_app_child_change", args=[pair.child.pk])
            header_image = _child_image_url(pair.child)
            header_ended = _child_has_left(pair.child, today) or pair.child.status == StatusChoices.SUPPORT
            header_badges = _child_badges(pair.child)
            leaf_name = str(pair.parent)
            leaf_url = reverse("admin:admin_app_adoptionparent_change", args=[pair.parent.pk])
            leaf_image = ""
            group_sort = (pair.child.name.lower(), pair.child.pk)
            leaf_sort = (pair.parent.first_name.lower(), pair.parent.last_name.lower(), pair.parent.pk)
        else:
            key = pair.parent.pk
            header_name = str(pair.parent)
            header_url = reverse("admin:admin_app_adoptionparent_change", args=[pair.parent.pk])
            header_image = ""
            header_ended = not pair.parent.active
            header_badges = [_("Inactive")] if not pair.parent.active else []
            leaf_name = str(pair.child)
            leaf_url = reverse("admin:admin_app_child_change", args=[pair.child.pk])
            leaf_image = _child_image_url(pair.child)
            group_sort = (pair.parent.first_name.lower(), pair.parent.last_name.lower(), pair.parent.pk)
            leaf_sort = (pair.child.name.lower(), pair.child.pk)

        group = grouped.get(key)
        if group is None:
            group = {
                "id": f"{axis}-{key}",
                "name": header_name,
                "url": header_url,
                "ended": header_ended,
                "badges": header_badges,
                "image_url": header_image,
                "sort": group_sort,
                "leaves": [],
            }
            grouped[key] = group

        leaf_badges = _link_badges(pair)
        if axis == AXIS_PARENTS:
            leaf_badges = leaf_badges + _child_badges(pair.child)
        group["leaves"].append((
            leaf_sort,
            GridLeaf(
                name=leaf_name,
                url=leaf_url,
                ended=_is_ended(pair, today),
                badges=leaf_badges,
                cells=[_cell(pair, item) for item in years],
                image_url=leaf_image,
                parent_id=pair.parent.pk,
                child_id=pair.child.pk,
            ),
        ))

    ordered = sorted(grouped.values(), key=lambda group: group["sort"])
    groups = []
    for group in ordered:
        leaves = [leaf for _sort, leaf in sorted(group["leaves"], key=lambda item: item[0])]
        groups.append(GridGroup(
            id=group["id"],
            name=group["name"],
            url=group["url"],
            ended=group["ended"],
            badges=group["badges"],
            leaves=leaves,
            sums=_sums(leaves, years),
            image_url=group["image_url"],
        ))
    return groups


def _sums(leaves, years):
    sums = []
    for index, year in enumerate(years):
        amounts = []
        for leaf in leaves:
            for payment in leaf.cells[index].payments:
                amounts.append(round(float(payment.amount) * 100))
        if not amounts:
            sums.append(YearSum(year=year, total=None))
        else:
            sums.append(YearSum(year=year, total=sum(amounts) / 100))
    return sums
