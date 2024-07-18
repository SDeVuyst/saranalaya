from decimal import Decimal
import json
from django.forms import ValidationError
from .models import Event, Ticket, Participant, Payment
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from payments import get_payment_model, RedirectNeeded
from django.utils.translation import gettext_lazy as _
from .utils import helpers
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required



def eventpage(request, id):
    event = get_object_or_404(Event, pk=id)
    tickets = get_list_or_404(Ticket, pk=event.id)

    context = {
        'event': event,
        'tickets': tickets
    }

    return render(request, 'event.html', context)


def buy_ticket(request, event_id):
    if request.method == "POST":

        # get form data
        first_name = request.POST.get('ticket-form-first-name')
        last_name = request.POST.get('ticket-form-name')
        mail = request.POST.get('ticket-form-email')
        
        event = get_object_or_404(Event, pk=event_id)
        possible_tickets = get_list_or_404(Ticket, pk=event_id)

        tickets = {}
        for possible_ticket in possible_tickets:
            amount_of_tickets = request.POST.get(f'ticket-form-number-{possible_ticket.pk}')
            if amount_of_tickets is not None:
                tickets[possible_ticket] = int(amount_of_tickets)

        # validation
        for key, value in tickets.items():
            if value < 1:
                raise ValidationError(
                    _("Invalid tickets: %(value)s"),
                    code="invalid",
                    params={"value": value},
                )

        if not helpers.emailIsValid(mail):
            raise ValidationError(
                _("Invalid email: %(mail)s"),
                code="invalid",
                params={"mail": mail},
            )
        
        # TODO check if tickets and/or event are not sold out


        total_cost = sum([amount*ticket.price.amount for ticket, amount in tickets.items()])

        # create the corresponding objects
        # payment object
        payment = Payment.objects.create(
            variant='default',
            description=event.title,
            total=Decimal(total_cost),
            currency='EUR',
            billing_first_name=first_name,
            billing_last_name=last_name,
        )
        payment.save()

        # every ticket needs its own participant object
        for ticket, amount in tickets.items():
            for i in range(amount):
                p = Participant.objects.create(
                    first_name = first_name,
                    last_name = last_name,
                    mail = mail,
                    payment_id = payment.pk,
                    attended = False,
                    ticket_id = ticket.pk
                )

                p.save()

        # go to the payment page
        return redirect(f"/events/payment-details/{payment.id}") 

    else:
        return HttpResponseRedirect(f"/events/{event_id}/")


def payment_details(request, payment_id):
    payment = get_object_or_404(get_payment_model(), id=payment_id)

    try:
        form = payment.get_form(data=request.POST or None)

    except RedirectNeeded as redirect_to:
        return redirect(str(redirect_to))
    
    return TemplateResponse(request, "payment.html", {"form": form, "payment": payment})


def payment_success(request, payment_id):
    event = Event.objects.latest()
    return TemplateResponse(request, "paymentcallback.html", {"title": "Betaling geslaagd!", "event_id": event.id})


def payment_failure(request, payment_id):
    event = Event.objects.latest()
    return TemplateResponse(request, "paymentcallback.html", {"title": "Oeps, er ging iets mis!", "event_id": event.id})


@csrf_exempt
def set_attendance(request):

    if request.method == 'POST':

        # get data from request
        data = json.loads(request.body)
        participant_id = data.get('participant_id')
        seed = data.get('seed')

        # validation
        if participant_id is None or seed is None:
            return JsonResponse({'success': False, 'message': _("QR code not recognised!")}, status=400)
        
        participant = get_object_or_404(Participant, pk=participant_id)

        # check if seed is correct
        if seed != participant.random_seed:
            print(seed)
            print(participant.random_seed)
            return JsonResponse({'success': False, 'message': _("Fraud Detected!")}, status=400)

        # validation
        if participant.attended:
            return JsonResponse({'success': False, 'message': _("Participant already attended!")}, status=400)
        

        participant.attended = True
        participant.save()

        return JsonResponse({'success': True, 'message': _("Attendance set!")})
    
    return JsonResponse({'success': False, 'message': _("unknown request.")}, status=400)


@staff_member_required
def scanner(request):
    return TemplateResponse(request, "scanner.html")