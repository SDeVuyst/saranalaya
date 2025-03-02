import json
from django.db.models import Sum
from django.http import HttpResponse
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.template.response import TemplateResponse
from .utils.helper import percentage_change
import datetime

from django.utils.safestring import mark_safe

from .utils.helper import *


def index(request):
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


def generate_mailto_link(request):
    # Get email addresses from the query parameters
    email_addresses = request.GET.get('emails', '')
    
    # Escape email addresses to ensure safety
    escaped_emails = escape(email_addresses)
    
    # Split email addresses into a list
    email_list = escaped_emails.split(',')
    
    # Define a maximum number of addresses per mailto link
    MAX_EMAILS_PER_LINK = 50
    
    # Split the email addresses into smaller groups
    email_groups = [email_list[i:i + MAX_EMAILS_PER_LINK] for i in range(0, len(email_list), MAX_EMAILS_PER_LINK)]
    
    # Generate buttons for each batch of email links
    buttons_html = ""
    for i, group in enumerate(email_groups):
        mailto_link = f"mailto:?bcc={','.join(group)}?subject=Important Information&body=Please review the following information."
        buttons_html += f"""
        <button onclick="window.open('{mailto_link}', '_blank')">Open Batch {i + 1}</button><br>
        """
    
    # Generate the HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Send Emails</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
            }}
            button {{
                display: inline-block;
                padding: 10px 20px;
                font-size: 16px;
                color: #fff;
                background-color: #007bff;
                border: none;
                border-radius: 5px;
                text-decoration: none;
                cursor: pointer;
                margin: 5px;
            }}
            button:hover {{
                background-color: #0056b3;
            }}
        </style>
    </head>
    <body>
        <p>Click on the buttons below to open each batch of email addresses:</p>
        {buttons_html}
        <p><a href="javascript:history.back()" class="button">Go Back</a></p>
    </body>
    </html>
    """
    
    return HttpResponse(html_content, content_type='text/html')


