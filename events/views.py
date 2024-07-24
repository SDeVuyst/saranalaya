import json
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.forms import ValidationError
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import (get_list_or_404, get_object_or_404, redirect,
                              render)
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from .models import Event, Participant, Payment, Ticket
from .utils import helpers
from .payment import MollieClient


def eventpage(request, id):
    event = get_object_or_404(Event, pk=id)
    tickets = get_list_or_404(Ticket, event_id=event.id)

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
        possible_tickets = get_list_or_404(Ticket, event_id=event_id)

        if not event.enable_selling:
            raise ValidationError(
                _("Event is not selling tickets"),
                code="invalid",
                params={},
            )

        tickets = {}
        for possible_ticket in possible_tickets:
            amount_of_tickets = request.POST.get(f'ticket-form-number-{possible_ticket.pk}')
            if amount_of_tickets != '':
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

        total_cost = sum([amount*ticket.price.amount for ticket, amount in tickets.items()])

        # create the corresponding objects
        # payment object
        payment = Payment.objects.create(
            first_name=first_name,
            last_name=last_name,
            mail=mail,
            amount=Decimal(total_cost)
        )
        
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
        payment.save()

        # create the mollie payment
        mollie_payment = MollieClient().create_mollie_payment(
            amount=Decimal(total_cost),
            description=event.title,
            payment_id=payment.pk
        )

        payment.mollie_id = mollie_payment.id
        payment.save()

        # go to the payment page
        return redirect(mollie_payment.checkout_url) 

    else:
        return HttpResponseRedirect(f"/events/{event_id}/")


def payment_success(request, payment_id):
    event = Event.objects.latest()
    return TemplateResponse(request, "paymentcallback.html", {"title": "Betaling geslaagd!", "description": "Check uw email (ook postvak ongewenst!) voor de tickets", "event_id": event.id})


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
            return JsonResponse({'success': False, 'message': _("Fraud Detected!")}, status=400)
        
        # validation
        if participant.attended:
            return JsonResponse({'success': False, 'message': _("Participant already attended!")}, status=400)
        

        participant.attended = True
        participant.save()

        return JsonResponse({'success': True, 'message': str(participant.ticket)})
    
    return JsonResponse({'success': False, 'message': _("unknown request.")}, status=400)


@staff_member_required
def scanner(request):
    return TemplateResponse(request, "scanner.html")


def beleid(request):
    return TemplateResponse(request, "beleid.html")

@csrf_exempt
def mollie_webhook(request):
    if request.method == 'POST':
        if 'id' not in request.POST:
            return HttpResponse(status=400)

        mollie_payment_id = request.POST['id']
        mollie_payment = MollieClient().client.payments.get(mollie_payment_id)
        payment = get_object_or_404(Payment, mollie_id=mollie_payment_id)

        payment.status = mollie_payment.get("status").lower()
        payment.save()

        return HttpResponse(status=200)

    return HttpResponseNotFound("Invalid request method")