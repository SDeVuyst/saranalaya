from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from payments.models import BasePayment
from djmoney.models.fields import MoneyField
from ckeditor.fields import RichTextField


class Payment(BasePayment):

    history = HistoricalRecords(verbose_name=_("History"))



class Event(models.Model):

    def __str__(self) -> str:
        return self.title
    
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


class Ticket(models.Model):

    def __str__(self) -> str:
        return self.title
    
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))
    price = MoneyField(verbose_name="Price", default_currency="EUR", max_digits=10, decimal_places=2)
    max_participants = models.IntegerField(verbose_name=_("Max Participants"))
    event = models.ForeignKey(Event, verbose_name=_("Event"), on_delete=models.RESTRICT)

    history = HistoricalRecords(verbose_name=_("History"))


class Participant(models.Model):

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.amount_of_people})" 
    
    first_name = models.CharField(max_length=50, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=50, verbose_name=_("Last Name"))
    mail = models.EmailField(verbose_name=_("Email"), max_length=254)
    payment = models.ForeignKey(Payment, on_delete=models.RESTRICT, verbose_name="Payment")
    attended = models.BooleanField(verbose_name=_("Attended"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    ticket = models.ForeignKey(Ticket, verbose_name=_("Ticket"), on_delete=models.RESTRICT)
    
    history = HistoricalRecords(verbose_name=_("History"))
