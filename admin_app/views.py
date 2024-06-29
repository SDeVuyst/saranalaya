from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Sum
from django.db.models.functions import ExtractYear
from django.utils.translation import gettext as _

from admin_app.models import Donation, AdoptionParentSponsoring
from .utils.helper import *


@staff_member_required
def get_filter_options(request):
    grouped_donations = Donation.objects.annotate(year=ExtractYear("date")).values("year").order_by("-year").distinct()
    options = [donation["year"] for donation in grouped_donations]

    return JsonResponse({
        "options": options,
    })


@staff_member_required
def donations_per_year_chart(request):

    valid_years = get_years_from_request(request)

    donations = Donation.objects.all()
    years = donations.values("date__year").order_by("date__year").distinct()
    years = [str(y['date__year']) for y in years]

    # make sure only the correct years are selected, last 5 years if years not specified
    valid_years = years[-5:] if valid_years == [] else valid_years
    years = list(filter(lambda year: year in valid_years, years))

    return JsonResponse({
        "data": {
            "labels": [str(year) for year in years],
            "datasets": [{
                "label": "Amount (€)",
                "data": [
                    donations.filter(date__year=y).aggregate(Sum("amount"))['amount__sum'] for y in years
                ],
                "hoverOffset": 4
            }]
        }
    })


@staff_member_required
def money_ratio_chart(request):

    donations = Donation.objects.all()
    parent_sponsors = AdoptionParentSponsoring.objects.all()

    years = get_years_from_request(request)
    year = get_last_available_adoption_sponsoring_year(parent_sponsors) if years == [] else years[0]

    total_donations_in_year = donations.filter(date__year=year).aggregate(Sum("amount"))['amount__sum']
    total_parent_sponsors_in_year = parent_sponsors.filter(date__year=year).aggregate(Sum("amount"))['amount__sum']

    return JsonResponse({
        "data": {
            "labels": [_("Donations"), _("Parent Sponsors")],
            "datasets": [{
                "label": "Amount (€)",
                "data": [
                    total_donations_in_year if total_donations_in_year is not None else 0,
                    total_parent_sponsors_in_year if total_parent_sponsors_in_year is not None else 0,
                ],
                "hoverOffset": 4
            }]
        }
    })


