from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum
from django.db.models.functions import ExtractYear

from admin_app.models import Donation
from admin_app.utils.charts import months, colorPrimary, colorSuccess, colorDanger, generate_color_palette, get_year_dict


@staff_member_required
def get_filter_options(request):
    grouped_donations = Donation.objects.annotate(year=ExtractYear("date")).values("year").order_by("-year").distinct()
    options = [donation["year"] for donation in grouped_donations]

    return JsonResponse({
        "options": options,
    })


@staff_member_required
def donations_per_year_chart(request):

    donations = Donation.objects.all()
    years = donations.values("date__year").distinct()
    years = [y['date__year'] for y in years]

    return JsonResponse({
        "title": f"Donations per year",
        "data": {
            "labels": [str(year) for year in years],
            "datasets": [{
                "label": "Amount (€)",
                "backgroundColor": [colorSuccess, colorDanger],
                "borderColor": [colorSuccess, colorDanger],
                "data": [
                    donations.filter(date__year=y).aggregate(Sum("amount")) for y in years
                ],
            }]
        },
    })