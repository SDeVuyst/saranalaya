import json

from django.conf import settings
from django.http import BadHeaderError, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from .models import Child, ExtraImage, News, StatusChoices
from django.db.models import Sum, Case, When, Value, IntegerField
from django.core.mail import send_mail
from email.utils import formataddr
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.template.response import TemplateResponse
from .utils.helper import percentage_change, verify_recaptcha
from .filters import KindFilter, NewsFilter
from .forms import ContactForm
import datetime

from django.utils.safestring import mark_safe

from .utils.helper import *


def index(request):
    kinderen = Child.objects.filter(show_on_website=True).order_by('status', '-date_of_admission')[:3]
    for index, kind in enumerate(kinderen):
        kind.delay = (index + 1) * 100

    nieuws = News.objects.all().order_by('-last_updated')[:3]
    kinderen_count = Child.objects.all().count()
    context = {
        'kinderen': kinderen,
        'nieuws': nieuws,
        'kinderen_tekst': _('Helped {count} children through the years').format(count=kinderen_count),
    }

    return TemplateResponse(request, "pages/index.html", context)

def kinderen(request):
    queryset = Child.objects.filter(show_on_website=True).annotate(
        status_order=Case(
            When(status=StatusChoices.ACTIVE, then=Value(1)),
            When(status=StatusChoices.SUPPORT, then=Value(2)),
            When(status=StatusChoices.LEFT, then=Value(3)),
            output_field=IntegerField()
        )
    ).order_by('status_order', '-date_of_admission')
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


def kind_detail(request, id):
    kind = get_object_or_404(Child, id=id)
    extra_images = ExtraImage.objects.filter(child_id=kind.id, active=True).order_by('-order')
    if kind.sibling_group is not None:
        siblings = kind.sibling_group.siblings.exclude(id=kind.id)
    else:
        siblings = None
        
    if kind.show_on_website == False:
        raise Http404("Child not found.")

    context = {
        'kind': kind,
        'siblings': siblings,
        'extra_images': extra_images
    }
    return TemplateResponse(request, "pages/kind_detail.html", context)

def over_ons(request):
    context = {}

    return TemplateResponse(request, "pages/over-ons.html", context)

def steun_ons(request):
    context = {}

    return TemplateResponse(request, "pages/steun-ons.html", context)

def nieuws(request):
    queryset = News.objects.filter(show_on_website=True).order_by('-date')
    filterset = NewsFilter(request.GET, queryset=queryset)
    artikels = filterset.qs

    paginator = Paginator(artikels, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'filter': filterset,
        'artikels': page_obj,  # Pass paginated queryset to template
    }

    return TemplateResponse(request, "pages/nieuws.html", context)

def nieuws_detail(request, id):
    artikel = get_object_or_404(News, id=id)

    if artikel.show_on_website == False:
        raise Http404("Article not found.")

    context = {
        'artikel': artikel,
    }
    return TemplateResponse(request, "pages/artikel_detail.html", context)

def contact(request):
    # request must always be post
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    
    if not verify_recaptcha(request.GET.get('recaptcha_token')):
        return JsonResponse({
            'success': False,
            'error': "reCAPTCHA gefaald. Gelieve opnieuw te proberen."
        })

    form = ContactForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'success': False, 'error': 'Form is not valid.'})
    
    name =  form.cleaned_data['name']
    email = form.cleaned_data['email']
    subject = form.cleaned_data['subject']
    message = form.cleaned_data['message']

    try:
        # Send mail to admins
        send_mail(
            f'Contact Form - {subject}',
            f'Name: {name}\nEmail: {email}\nMessage: {message}',
            formataddr(('Contact | Care India', settings.EMAIL_HOST_USER)),
            [settings.EMAIL_HOST_USER],
            fail_silently=False,
        )

        # Send confirmation mail to user
        send_mail(
            _('Message Received'),
            _("Thank you for completing the contact form. We have received your message in good order and will contact you as soon as possible.\n\nKind regards\n\nThe Care India Team"),
            formataddr(('Contact | Care India', settings.EMAIL_HOST_USER)),
            [email],
            fail_silently=False
        )

        return JsonResponse({'success': True})
    
    except BadHeaderError:
        return JsonResponse({'success': False, 'error': 'Invalid header found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def redirect_to_events(request):
    request.urlconf = 'events.urls'
    return reverse('events:index')


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
