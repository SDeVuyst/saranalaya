import io
from typing import Iterable
import secrets
import string
from django.http import HttpResponse
import qrcode
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from payments.models import BasePayment, PaymentStatus
from djmoney.models.fields import MoneyField
from ckeditor.fields import RichTextField
from django.utils import timezone
from django.utils.html import strip_tags
from django.db.models import Q
from django.contrib.staticfiles import finders
from .templatetags import dutch_date
from .utils import helpers


class Event(models.Model):

    def __str__(self) -> str:
        return self.title
    
    class Meta:
        get_latest_by = "pk"
    
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    description = RichTextField(verbose_name=_("Description"))
    start_date = models.DateTimeField(verbose_name=_("Start Date"))
    end_date = models.DateTimeField(verbose_name=_("End Date"))
    max_participants = models.IntegerField(verbose_name=_("Max Participants"))
    location_short = models.CharField(max_length=50, verbose_name=_("Location (short)"))
    location_long = RichTextField(verbose_name=_("Location (long)"))
    image = models.ImageField(verbose_name=_("Image"), upload_to="events")
    google_maps_embed_url = models.URLField(verbose_name=_("Google Maps embed URL"), max_length=512)

    history = HistoricalRecords(verbose_name=_("History"))

    @property
    def is_in_future(self):
        return timezone.now() < self.start_date
    
    @property
    def is_same_day(self):
        return self.start_date.strftime("%d/%m/%Y") == self.end_date.strftime("%d/%m/%Y")
    
    @property
    def is_sold_out(self):
        # Total participants limit exceeded
        total_participants = sum(ticket.participants_count for ticket in self.ticket_set.all())
        total = total_participants >= self.max_participants
        if total: return total

        # All tickets have their max participants limit exceeded
        tickets_are_sold_out = all(ticket.is_sold_out for ticket in self.ticket_set.all())
        return tickets_are_sold_out 


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
            Q(payment__status=PaymentStatus.CONFIRMED) | 
            Q(payment__status=PaymentStatus.WAITING) |
            Q(payment__status=PaymentStatus.PREAUTH) |
            Q(payment__status=PaymentStatus.INPUT)
        ).count()
        return amount_of_participants_with_this_as_ticket >= self.max_participants
    
    @property
    def remaining_tickets(self):
        amount_of_participants_with_this_as_ticket = Participant.objects.filter(ticket_id=self.pk).count()
        return self.max_participants - amount_of_participants_with_this_as_ticket
    
    @property
    def participants_count(self):
        return Participant.objects.filter(ticket_id=self.pk).filter(
            Q(payment__status=PaymentStatus.CONFIRMED) | 
            Q(payment__status=PaymentStatus.WAITING) |
            Q(payment__status=PaymentStatus.PREAUTH) |
            Q(payment__status=PaymentStatus.INPUT)
        ).count()


class Payment(BasePayment):

    def get_failure_url(self) -> str:
        # Return a URL where users are redirected after
        # they fail to complete a payment:
        return f"http://localhost:8100/events/ticket/{self.pk}/failure"

    def get_success_url(self) -> str:
        # Return a URL where users are redirected after
        # they successfully complete a payment:
        return f"http://localhost:8100/events/ticket/{self.pk}/success"
    

    def get_purchased_items(self) -> Iterable[Ticket]:

        # get all participants with this payment
        participants = Participant.objects.filter(payment=self)
        for participant in participants:
            yield participant.ticket

    def generate_ticket(self):
        participants = Participant.objects.filter(payment=self)
        tickets = []
        for p in participants:
            ticket = p.generate_ticket(return_as_http=False) 

            tickets.append(ticket)

            
        merged_buffer = helpers.merge_pdfs(tickets)
        response = HttpResponse(merged_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="tickets-{self.pk}.pdf"'

        return response
        

    history = HistoricalRecords(verbose_name=_("History"))


class Participant(models.Model):

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}" 
    
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

        # Draw the QR code image onto the PDF
        p.drawImage(temp_path, 400, 590, 170, 170)

        # Add Care India logo
        logo_path = finders.find('images/logo-with-bg.jpg')
        p.drawImage(logo_path, 100, 730, 427 * 0.3, 58 * 0.3)

        # get info about event
        event = self.ticket.event
        if dutch_date.dutch_date(event.start_date) == dutch_date.dutch_date(event.end_date):
            formatted_date = f"{dutch_date.dutch_datetime(event.start_date)} - {dutch_date.dutch_time(event.end_date)}"
        else:
            formatted_date = f"{dutch_date.dutch_datetime(event.start_date)} - {dutch_date.dutch_datetime(event.end_date)}"

        # Add ticket details
        # Set correct font for title
        font_path = finders.find('fonts/Outfit-Bold.ttf')
        pdfmetrics.registerFont(TTFont('Outfit', font_path))
        p.setFont("Outfit", 25)
        p.drawString(100, 690, str(event))

        # Set correct font for description
        font_path = finders.find('fonts/Outfit-Regular.ttf')
        pdfmetrics.registerFont(TTFont('Outfit', font_path))
        p.setFont("Outfit", 18)

        p.drawString(100, 660, formatted_date)
        p.drawString(100, 635, str(self.ticket))
        p.drawString(100, 610, strip_tags(event.location_long))

        # Finalize the PDF
        p.save()

        # Get the value of the BytesIO buffer and write it to the response
        buffer.seek(0)

        if not return_as_http:
            return buffer
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="ticket-{self.pk}.pdf"'

        return response