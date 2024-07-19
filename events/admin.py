from django.contrib import admin
from django.http import HttpResponse
from .models import *
from django.utils.translation import gettext as _
from django.contrib import admin
from django.shortcuts import get_object_or_404
from unfold.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from admin_app.sites import saranalaya_admin_site
from payments.models import PaymentStatus
from unfold.contrib.inlines.admin import StackedInline  
from unfold.decorators import action, display
from io import BytesIO
from unfold.contrib.filters.admin import RelatedDropdownFilter


# INLINES #
class TicketInline(StackedInline):
    model = Ticket
    verbose_name = _("Event Ticket")
    verbose_name_plural = _("Event Tickets")


# FILTERS #


# MODELS #
@admin.register(Event, site=saranalaya_admin_site)
class EventAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('title', 'location_short', 'is_sold_out')
    ordering = ('id',)
    exclude = ('tickets',)

    search_fields = ('title', 'description', 'start_date', 'end_date', 'location',)

    inlines = [
        TicketInline
    ]

    @display(
        description=_("Sold out"),
        label={
            _("Sold out!"): "danger",
            _("Available"): "success"
        }
    )
    def is_sold_out(self, obj):
        return _("Sold out!") if obj.is_sold_out else _("Available")


@admin.register(Participant, site=saranalaya_admin_site)
class ParticipantAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ['first_name', 'last_name', 'payment_status', 'attendance']
    ordering = ('id',)

    @display(
        description=_('Payment Status'), 
        label={
            PaymentStatus.WAITING: "warning",
            PaymentStatus.PREAUTH: "warning",
            PaymentStatus.CONFIRMED: "success",
            PaymentStatus.REJECTED: "danger",
            PaymentStatus.REFUNDED: "info",
            PaymentStatus.ERROR: "danger",
            PaymentStatus.INPUT: "danger",
        },
        header=True,
    )
    def payment_status(self, obj):
        return obj.payment.status
    
    @display(
        description=_("Attended"),
        label={
            _("Yes"): "success",
            _("No"): "danger"
        }
    )
    def attendance(self, obj):
        return _("Yes") if obj.attended else _("No")
    

    search_fields = ('first_name', 'last_name', 'mail')
    list_filter = (
        ('attended', admin.BooleanFieldListFilter),
        ('ticket', RelatedDropdownFilter),
        ('ticket__event', RelatedDropdownFilter)
    )

    list_filter_submit = True
    actions_detail = ["generate_ticket", "generate_qr_code"]

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
    
    @action(description=_("Generate Ticket"))
    def generate_ticket(modeladmin, request, object_id: int):
        participant = get_object_or_404(Participant, pk=object_id)

        return participant.generate_ticket()



@admin.register(Payment, site=saranalaya_admin_site)
class PaymentAdmin(SimpleHistoryAdmin, ModelAdmin):
    actions_detail = ["generate_ticket",]

    @action(description=_("Generate Ticket"))
    def generate_ticket(modeladmin, request, object_id: int):
        p = get_object_or_404(Payment, pk=object_id)

        return p.generate_ticket()


@admin.register(Ticket, site=saranalaya_admin_site)
class TicketAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('title', 'price', 'is_sold_out')
    ordering = ("id",)

    search_fields = ('title', 'description')

    list_filter = (
        ('event', RelatedDropdownFilter),
    )

    list_filter_submit = True


    @display(
        description=_("Sold out"),
        label={
            "Sold out!": "danger",
            "Available": "success"
        }
    )
    def is_sold_out(self, obj):
        return "Sold out!" if obj.is_sold_out else "Available"