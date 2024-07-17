from django.contrib import admin
from django.http import HttpResponse
from .models import *
from django.utils.translation import gettext as _
from django.contrib import admin
from unfold.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from admin_app.sites import saranalaya_admin_site
from payments.models import PaymentStatus
from unfold.contrib.inlines.admin import StackedInline  
from unfold.decorators import action, display
import qrcode
from io import BytesIO
    

# INLINES #
class TicketInline(StackedInline):
    model = Ticket
    verbose_name = _("Event Ticket")
    verbose_name_plural = _("Event Tickets")


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
            "Sold out!": "danger",
            "Available": "success"
        }
    )
    def is_sold_out(self, obj):
        return "Sold out!" if obj.is_sold_out else "Available"


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
            True: "success",
            False: "danger"
        }
    )
    def attendance(self, obj):
        return obj.attended
    

    search_fields = ('first_name', 'last_name', 'mail')
    list_filter = (
        ('attended', admin.BooleanFieldListFilter),
    )

    list_filter_submit = True
    actions_detail = ["generate_qr_code"]

    @action(description=_("Generate QR-code"))
    def generate_qr_code(modeladmin, request, object_id: int):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f'participant_id:{object_id}')
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename=ticket_{object_id}_qr.png'
        return response



@admin.register(Payment, site=saranalaya_admin_site)
class PaymentAdmin(SimpleHistoryAdmin, ModelAdmin):
    pass


@admin.register(Ticket, site=saranalaya_admin_site)
class TicketAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('title', 'price', 'is_sold_out')
    ordering = ("id",)

    search_fields = ('title', 'description')

    @display(
        description=_("Sold out"),
        label={
            "Sold out!": "danger",
            "Available": "success"
        }
    )
    def is_sold_out(self, obj):
        return "Sold out!" if obj.is_sold_out else "Available"