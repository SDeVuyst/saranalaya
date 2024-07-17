from typing import Iterable
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from payments.models import BasePayment
from djmoney.models.fields import MoneyField
from ckeditor.fields import RichTextField
from django.utils import timezone




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


class Ticket(models.Model):

    def __str__(self) -> str:
        return self.title
    
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))
    price = MoneyField(verbose_name="Price", default_currency="EUR", max_digits=10, decimal_places=2)
    max_participants = models.IntegerField(verbose_name=_("Max Participants"))
    event = models.ForeignKey(Event, verbose_name=_("Event"), on_delete=models.RESTRICT)

    history = HistoricalRecords(verbose_name=_("History"))


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
    
    history = HistoricalRecords(verbose_name=_("History"))
