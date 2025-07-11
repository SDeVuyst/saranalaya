import secrets
import string
from email.utils import formataddr
from io import BytesIO
from typing import Iterable

import pytz
import qrcode
from ckeditor.fields import RichTextField
from django.conf import settings
from django.utils.translation import pgettext_lazy
from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from simple_history.models import HistoricalRecords

from .templatetags import dutch_date
from .utils import helpers


class Event(models.Model):

    def __str__(self) -> str:
        return self.title
    
    class Meta:
        get_latest_by = "pk"
    
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    titel_sub = models.CharField(max_length=100, verbose_name=_("Title Subscript"))
    description = RichTextField(verbose_name=_("Description"))
    email_text = RichTextField(verbose_name=_("Email Text"))
    start_date = models.DateTimeField(verbose_name=_("Start Date"))
    end_date = models.DateTimeField(verbose_name=_("End Date"))
    max_participants = models.IntegerField(verbose_name=_("Max Participants"))
    location_short = models.CharField(max_length=50, verbose_name=_("Location (short)"))
    location_long = RichTextField(verbose_name=_("Location (long)"))
    image = models.ImageField(verbose_name=_("Image"), upload_to="events")
    google_maps_embed_url = models.URLField(verbose_name=_("Google Maps embed URL"), max_length=512)
    enable_selling = models.BooleanField(verbose_name=_("Enable Selling"), default=True)

    history = HistoricalRecords(verbose_name=_("History"))

    @property
    def is_in_future(self):
        brussels_tz = pytz.timezone('Europe/Brussels')
        now = timezone.now().astimezone(brussels_tz)
        start_date_brussels = self.start_date.astimezone(brussels_tz)
        return now < start_date_brussels
    
    @property
    def is_same_day(self):
        return self.start_date.strftime("%d/%m/%Y") == self.end_date.strftime("%d/%m/%Y")
    
    @property
    def is_sold_out(self):
        # Total participants limit exceeded
        event_sold_out = self.participants_count >= self.max_participants

        # All tickets have their max participants limit exceeded
        tickets_are_sold_out = all(ticket.is_sold_out for ticket in self.ticket_set.all())

        return tickets_are_sold_out or event_sold_out

    @property
    def remaining_tickets(self):
        return self.max_participants - self.participants_count
    
    @property
    def participants_count(self):
        return sum(ticket.participants_count for ticket in self.ticket_set.all())


class Ticket(models.Model):

    def __str__(self) -> str:
        return self.title
    
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))
    price = MoneyField(verbose_name="Price", default_currency="EUR", max_digits=10, decimal_places=2)
    max_participants = models.IntegerField(verbose_name=_("Max Participants"))
    event = models.ForeignKey(Event, verbose_name=_("Event"), on_delete=models.RESTRICT)

    history = HistoricalRecords(verbose_name=_("History"))

    @property 
    def is_sold_out(self):
        amount_of_participants_with_this_as_ticket = Participant.objects.filter(ticket_id=self.pk).filter(
            Q(payment__status=PaymentStatus.PAID) | 
            Q(payment__status=PaymentStatus.OPEN)
        ).count()
        return amount_of_participants_with_this_as_ticket >= self.max_participants
    
    @property
    def remaining_tickets(self):
        amount_of_participants_with_this_as_ticket = Participant.objects.filter(ticket_id=self.pk).count()
        return self.max_participants - amount_of_participants_with_this_as_ticket
    
    @property
    def participants_count(self):
        return Participant.objects.filter(ticket_id=self.pk).filter(
            Q(payment__status=PaymentStatus.PAID) | 
            Q(payment__status=PaymentStatus.OPEN)
        ).count()



class PaymentStatus:
    PAID = "paid"
    AUTHORIZED = "authorized"
    OPEN = "open"
    CANCELED = "canceled"
    EXPIRED = "expired"
    FAILED = "failed"


    CHOICES = [
        (PAID, pgettext_lazy("payment status", "Paid")),
        (OPEN, pgettext_lazy("payment status", "Open")),
        (CANCELED, pgettext_lazy("payment status", "Canceled")),
        (EXPIRED, pgettext_lazy("payment status", "Expired")),
        (FAILED, pgettext_lazy("payment status", "Failed"))
    ]


class Payment(models.Model):
    
    def save(self, *args, **kwargs):
        # Check if payment is received
        if self.status == PaymentStatus.PAID:
            self.send_mail()

        super().save(*args, **kwargs)


    mollie_id = models.CharField(verbose_name=_("Mollie id"), blank=True, null=True)
    first_name = models.CharField(max_length=50, verbose_name=_("First Name"), blank=True, null=True)
    last_name = models.CharField(max_length=50, verbose_name=_("Last Name"), blank=True, null=True)
    mail = models.EmailField(verbose_name=_("Email"), max_length=254, blank=True, null=True)
    status = models.CharField(max_length=10, choices=PaymentStatus.CHOICES, default=PaymentStatus.OPEN)
    amount = MoneyField(verbose_name="Price", default_currency="EUR", max_digits=10, decimal_places=2, blank=True, null=True)

    history = HistoricalRecords(verbose_name=_("History"))

    @property
    def success_url(self) -> str:
        # Return a URL where users are redirected after
        # they successfully complete a payment:
        return f"http://vanakaam.be/ticket/{self.pk}/success"


    def generate_ticket(self, for_email=False):
        participants = Participant.objects.filter(payment=self)
        tickets = []
        for p in participants:
            ticket = p.generate_ticket(return_as_http=False) 

            tickets.append(ticket)

            
        merged_buffer = helpers.merge_pdfs(tickets)
        if for_email: return merged_buffer

        response = HttpResponse(merged_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="tickets-{self.pk}.pdf"'

        return response

    def send_mail(self):
        # we only need first because all info is the same for the matching participants
        participant = Participant.objects.filter(payment=self).first()
        event = participant.ticket.event

        print(f"Sending confirmation email for event '{event.title}' to {participant.mail}")
        
        email_body = render_to_string('confirmation-email.html', {
            'event': event,
            'participant': participant,
        })

        # Generate tickets PDF
        tickets_pdf = self.generate_ticket(for_email=True)

        email = EmailMessage(
            'Saranalaya | Bevestiging',
            email_body,
            formataddr(('Evenementen | Saranalaya', settings.EMAIL_HOST_USER)),
            [participant.mail],
            bcc=[settings.EMAIL_HOST_USER]
        )
        email.content_subtype = 'html'

        # add tickets as attachment
        email.attach(f'tickets-{self.pk}.pdf', tickets_pdf.getvalue(), 'application/pdf')

        helpers.attach_image(email, "logo")
        helpers.attach_image(email, "facebook")
        helpers.attach_image(email, "mail")

        # Send the email
        email.send()



class Participant(models.Model):

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}" 
    
    class Meta:
        get_latest_by = "pk"
    
    first_name = models.CharField(max_length=50, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=50, verbose_name=_("Last Name"))
    mail = models.EmailField(verbose_name=_("Email"), max_length=254)
    payment = models.ForeignKey(Payment, on_delete=models.RESTRICT, verbose_name="Payment", blank=True, null=True)
    attended = models.BooleanField(verbose_name=_("Attended"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), on_delete=models.RESTRICT)

    # seed for the QR codes
    random_seed = models.CharField(max_length=10, verbose_name="Random Seed", editable=False)
    
    history = HistoricalRecords(verbose_name=_("History"))


    def save(self, *args, **kwargs):
        if not self.random_seed:
            self.random_seed = self._generate_random_seed()
        super().save(*args, **kwargs)

    def _generate_random_seed(self):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(10))
    
    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f'participant_id:{self.pk}')
        qr.add_data(f'seed:{self.random_seed}')

        qr.make(fit=True)

        return qr.make_image(fill='black', back_color='white')
    
    def generate_ticket(self, return_as_http=True):
        # Create a buffer to hold the PDF data
        buffer = BytesIO()

        # Create a canvas object
        p = canvas.Canvas(buffer, pagesize=letter)

        qr_img = self.generate_qr_code()

        # Save the QR code image to a BytesIO object
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        qr_image = Image.open(qr_buffer)
        temp_path = "/tmp/qr_code.png"
        qr_image.save(temp_path)

        print(f"QR code saved to {temp_path}")

        # Draw the QR code image onto the PDF
        p.drawImage(temp_path, 400, 590, 170, 170)

        print(f"QR code drawn on PDF at position (400, 590) with size (170, 170)")

        # Add Care India logo
        logo_path = finders.find('events/images/logo-with-bg.jpg')
        p.drawImage(logo_path, 100, 730, 427 * 0.3, 58 * 0.3)

        print(f"Logo drawn on PDF at position (100, 730) with size (128.1, 17.4)")

        # get info about event
        event = self.ticket.event
        if dutch_date.dutch_date(event.start_date) == dutch_date.dutch_date(event.end_date):
            formatted_date = f"{dutch_date.dutch_datetime(event.start_date)} - {dutch_date.dutch_time(event.end_date)}"
        else:
            formatted_date = f"{dutch_date.dutch_datetime(event.start_date)} - {dutch_date.dutch_datetime(event.end_date)}"

        # Add ticket details
        # Set correct font for title
        font_path = finders.find('events/fonts/Outfit-Bold.ttf')
        pdfmetrics.registerFont(TTFont('Outfit', font_path))
        p.setFont("Outfit", 25)
        p.drawString(100, 690, str(event))

        print(f"Event title '{event}' drawn on PDF at position (100, 690) with font size 25")

        # Set correct font for description
        font_path = finders.find('events/fonts/Outfit-Regular.ttf')
        pdfmetrics.registerFont(TTFont('Outfit', font_path))
        p.setFont("Outfit", 18)

        print(f"Description font set to 'Outfit' with size 18")

        p.drawString(100, 660, formatted_date)
        p.drawString(100, 635, str(self.ticket))
        p.drawString(100, 610, strip_tags(event.location_short))

        # Finalize the PDF
        p.save()

        # Get the value of the BytesIO buffer and write it to the response
        buffer.seek(0)

        if not return_as_http:
            return buffer
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="ticket-{self.pk}.pdf"'

        return response