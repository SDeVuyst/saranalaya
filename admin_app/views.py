import json
from .models import Child, News
from django.db.models import Sum
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.template.response import TemplateResponse
from .utils.helper import percentage_change
from .filters import KindFilter
import datetime

from django.utils.safestring import mark_safe

from .utils.helper import *


def index(request):
    kinderen = Child.objects.all().order_by('-date_of_admission')[:4]
    nieuws = News.objects.all().order_by('-last_updated')[:4]
    kinderen_count = Child.objects.all().count()
    context = {
        'kinderen': kinderen,
        'nieuws': nieuws,
        'kinderen_tekst': f'{kinderen_count} kinderen geholpen doorheen de jaren',
    }

    return TemplateResponse(request, "pages/index.html", context)

def kinderen(request):
    queryset = Child.objects.all().order_by('-date_of_admission')
    filterset = KindFilter(request.GET, queryset=queryset)
    kinderen = filterset.qs

    paginator = Paginator(kinderen, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'filter': filterset,
        'kinderen': page_obj,  # Pass paginated queryset to template
    }

    return TemplateResponse(request, "pages/kinderen.html", context)

def nieuws(request):
    context = {}

    return TemplateResponse(request, "pages/index.html", context)

def dashboard_callback(request, context):
    from .models import Donation, AdoptionParentSponsoring, Child, AdoptionParent, StatusChoices

    current_year = str(datetime.datetime.now().year)
    last_year = str(datetime.datetime.now().year -1)

    progress_text = _(f"progress from {last_year}")
    
    # Get donations and parent sponsors in every year
    all_years_donation = Donation.objects.all().values("date__year").order_by("date__year").distinct()
    all_years_donation = [str(y['date__year']) for y in all_years_donation]
    all_years_parent = AdoptionParentSponsoring.objects.all().values("date__year").order_by("date__year").distinct()
    all_years_parent = [str(y['date__year']) for y in all_years_parent]
    all_years = all_years_donation if len(all_years_donation) > len(all_years_parent) else all_years_parent # select longest years as years
    donation_data = [Donation.objects.filter(date__year=y).aggregate(Sum("amount"))['amount__sum'] for y in all_years]
    donation_data = [0 if val is None else val for val in donation_data]
    parent_sponsor_data = [AdoptionParentSponsoring.objects.filter(date__year=y).aggregate(Sum("amount"))['amount__sum'] for y in all_years]
    parent_sponsor_data = [0 if val is None else val for val in parent_sponsor_data]
    
    # Total amount of donations and parent sponsors this year
    total_donations_this_year = Donation.objects.filter(date__year=current_year).aggregate(Sum("amount"))['amount__sum']
    total_donations_this_year = total_donations_this_year if total_donations_this_year is not None else 0
    total_parent_sponsors_this_year = AdoptionParentSponsoring.objects.filter(date__year=current_year).aggregate(Sum("amount"))['amount__sum']
    total_parent_sponsors_this_year = total_parent_sponsors_this_year if total_parent_sponsors_this_year is not None else 0

    # Total amount of donations and parent sponsors last year
    total_donations_last_year = Donation.objects.filter(date__year=last_year).aggregate(Sum("amount"))['amount__sum']
    total_donations_last_year = total_donations_last_year if total_donations_last_year is not None else 0
    total_parent_sponsors_last_year = AdoptionParentSponsoring.objects.filter(date__year=last_year).aggregate(Sum("amount"))['amount__sum']
    total_parent_sponsors_last_year = total_parent_sponsors_last_year if total_parent_sponsors_last_year is not None else 0

    # Calculate the difference in percentage and set color (red or green for + or -)
    donations_change_percentage = int(percentage_change(total_donations_last_year, total_donations_this_year))
    donations_color_percentage = "green" if donations_change_percentage >= 0 else "red"
    parent_sponsor_change_percentage = int(percentage_change(total_parent_sponsors_last_year, total_parent_sponsors_this_year))
    parent_sponsor_color_percentage = "green" if parent_sponsor_change_percentage >= 0 else "red"

    # Calculate total amount of active children and active adoption parents
    amount_of_active_children = Child.objects.filter(status='a').count()
    amount_of_adoption_parents = AdoptionParent.objects.filter(active=True).count()

    # Get years of admission dates of children
    all_years_admission = Child.objects.all().values("date_of_admission__year").order_by("date_of_admission__year").distinct()
    all_years_admission = [str(y['date_of_admission__year']) for y in all_years_admission]

    # Get amount of children by admission year
    children_admission_data = [Child.objects.filter(date_of_admission__year=y).count() for y in all_years_admission]

    # Get amount of children by status
    children_statusses = [str(l) for l in StatusChoices.labels]
    children_status_data = [Child.objects.filter(status=s).count() for s in StatusChoices.values]


    # add data to context to be able to build the dashboard
    context.update(
        {
            "short_stats": [
                {
                    "title": _("Children"),
                    "year": _("Current"),
                    "metric": amount_of_active_children,
                    "footer": _("Only active children are counted"),
                },

                {
                    "title": _(f"Donations"),
                    "year": current_year,
                    "metric": f"€{total_donations_this_year}",
                    "footer": mark_safe(
                        f'<strong class="text-{donations_color_percentage}-600 font-medium">{donations_change_percentage}%</strong>&nbsp;{progress_text}'
                    ),
                },

                {
                    "title": _(f"Adoption Parents"),
                    "year": _("All Time"),
                    "metric": amount_of_adoption_parents,
                    "footer": _("Only active parents are counted"),
                },

                {
                    "title": _(f"Parent Payments"),
                    "year": current_year,
                    "metric": f"€{total_parent_sponsors_last_year}",
                    "footer": mark_safe(
                        f'<strong class="text-{parent_sponsor_color_percentage}-600 font-medium">{parent_sponsor_change_percentage}%</strong>&nbsp;{progress_text}'
                    ),
                }, 
                
            ],
            "chart": json.dumps(
                {
                    "labels": all_years,
                    "datasets": [
                        {
                            "label": _("Donations"),
                            "data": donation_data,
                            "type": "line",
                            "backgroundColor": "#f0abfc",
                            "borderColor": "#f0abfc",
                        },
                        {
                            "label": _("Parent Payments"),
                            "data": parent_sponsor_data,
                            "backgroundColor": "#9333ea",
                        },
                    ],
                }
            ),
            "children": [
                {
                    "title": _("Children"),
                    "metric": _("By Admission Date"),
                    "chart": json.dumps(
                        {
                            "labels": all_years_admission,
                            "datasets": [
                                {"data": children_admission_data, "borderColor": "#9333ea"}
                            ],
                        }
                    ),
                },

                {
                    "title": _("Children"),
                    "metric": _("By Status"),
                    "chart": json.dumps(
                        {
                            "labels": children_statusses,
                            "datasets": [
                                {"data": children_status_data, "borderColor": "#9333ea"}
                            ],
                        }
                    ),
                },
            ],
        },
    )

    return context
