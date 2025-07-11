from io import BytesIO

from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RelatedDropdownFilter
from unfold.contrib.inlines.admin import StackedInline
from unfold.decorators import action, display

from admin_app.sites import saranalaya_admin_site

from .models import *


# INLINES #
class TicketInline(StackedInline):
    model = Ticket
    verbose_name = _("Event Ticket")
    verbose_name_plural = _("Event Tickets")


# FILTERS #


# MODELS #
@admin.register(Event, site=saranalaya_admin_site)
class EventAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('title', 'participants_count', 'remaining_tickets', 'is_sold_out')
    ordering = ('id',)
    exclude = ('tickets',)

    search_fields = ('title', 'description', 'start_date', 'end_date', 'location',)

    inlines = [
        TicketInline
    ]

    @display(
        description=_("Sold out"),
        label={
            True: "danger",
            False: "success"
        }
    )
    def is_sold_out(self, obj):
        label = _("Sold out!") if obj.is_sold_out else _("Available")
        return obj.is_sold_out, label



@admin.register(Participant, site=saranalaya_admin_site)
class ParticipantAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ['first_name', 'last_name', 'payment_status', 'attendance']
    ordering = ('id',)

    @display(
        description=_('Payment Status'), 
        label={
            PaymentStatus.PAID: "success",
            PaymentStatus.OPEN: "warning",
            PaymentStatus.CANCELED: "danger",
            PaymentStatus.EXPIRED: "danger",
            PaymentStatus.FAILED: "danger",
        },
        header=True,
    )
    def payment_status(self, obj):
        return obj.payment.status
    
    @display(
        description=_("Attended"),
        label={
            True: "success",
            False: "danger"
        }
    )
    def attendance(self, obj):
        label = _("Yes") if obj.attended else _("No")
        return obj.attended, label
    

    search_fields = ('first_name', 'last_name', 'mail')
    list_filter = (
        ('attended', admin.BooleanFieldListFilter),
        ('ticket', RelatedDropdownFilter),
    )

    list_filter_submit = True
    actions_detail = ["generate_tickets", "generate_ticket", "generate_qr_code", "send_confirmation_email"]

    @action(description=_("Generate QR-code"))
    def generate_qr_code(modeladmin, request, object_id: int):

        participant = get_object_or_404(Participant, pk=object_id)

        img = participant.generate_qr_code()
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename=ticket_{object_id}_qr.png'
        return response
    
    @action(description=_("Generate All Tickets"))
    def generate_tickets(modeladmin, request, object_id: int):
        participant = get_object_or_404(Participant, pk=object_id)
        payment = get_object_or_404(Payment, pk=participant.payment.id)

        return payment.generate_ticket()
    
    @action(description=_("Generate Ticket"))
    def generate_ticket(modeladmin, request, object_id: int):
        participant = get_object_or_404(Participant, pk=object_id)

        return participant.generate_ticket()

    @action(description=_("Send Confirmation Email"))
    def send_confirmation_email(modeladmin, request, object_id: int):
        participant = get_object_or_404(Participant, pk=object_id)
        payment = get_object_or_404(Payment, pk=participant.payment.id)

        return payment.send_mail()


@admin.register(Payment, site=saranalaya_admin_site)
class PaymentAdmin(SimpleHistoryAdmin, ModelAdmin):
    actions_detail = ["generate_ticket",]

    @action(description=_("Generate Ticket"))
    def generate_ticket(modeladmin, request, object_id: int):
        p = get_object_or_404(Payment, pk=object_id)

        return p.generate_ticket()


@admin.register(Ticket, site=saranalaya_admin_site)
class TicketAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('title', 'price', 'participants_count', 'remaining_tickets', 'is_sold_out')
    ordering = ("id",)

    search_fields = ('title', 'description')

    @display(
        description=_("Sold out"),
        label={
            True: "danger",
            False: "success"
        }
    )
    def is_sold_out(self, obj):
        label = _("Sold out!") if obj.is_sold_out else _("Available")
        return obj.is_sold_out, label