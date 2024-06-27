from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum
from django.db.models.functions import ExtractYear

from admin_app.models import Donation


@staff_member_required
def get_filter_options(request):
    grouped_donations = Donation.objects.annotate(year=ExtractYear("date")).values("year").order_by("-year").distinct()
    options = [donation["year"] for donation in grouped_donations]

    return JsonResponse({
        "options": options,
    })


@staff_member_required
def donations_per_year_chart(request):

    valid_years = request.GET.getlist('years', None)
    valid_years = [year.replace('/', '') for year in valid_years]

    donations = Donation.objects.all()
    years = donations.values("date__year").order_by("date__year").distinct()
    years = [str(y['date__year']) for y in years]

    # make sure only the correct years are selected
    valid_years = years if valid_years is None else valid_years
    years = list(filter(lambda year: year in valid_years, years))

    return JsonResponse({
        "data": {
            "labels": [str(year) for year in years],
            "datasets": [{
                "label": "Amount (€)",
                "data": [
                    donations.filter(date__year=y).aggregate(Sum("amount"))['amount__sum'] for y in years
                ],
            }]
        }
    })