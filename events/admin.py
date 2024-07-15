from django.contrib import admin
from django.contrib import admin
from .models import *
from django.utils.translation import gettext as _
from django.contrib import admin
from unfold.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from admin_app.sites import saranalaya_admin_site
from unfold.contrib.inlines.admin import StackedInline  


# INLINES #
class TicketInline(StackedInline):
    model = Ticket
    verbose_name = _("Event Ticket")
    verbose_name_plural = _("Event Tickets")


# MODELS #
@admin.register(Event, site=saranalaya_admin_site)
class EventAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('title', 'location_short',)
    ordering = ('id',)
    exclude = ('tickets',)

    search_fields = ('title', 'description', 'start_date', 'end_date', 'location',)

    inlines = [
        TicketInline
    ]


@admin.register(Participant, site=saranalaya_admin_site)
class ParticipantAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('first_name', 'last_name', )
    ordering = ('id',)

    search_fields = ('first_name', 'last_name', 'mail')
    list_filter = (
        ('attended', admin.BooleanFieldListFilter),
    )

    list_filter_submit = True


@admin.register(Payment, site=saranalaya_admin_site)
class PaymentAdmin(SimpleHistoryAdmin, ModelAdmin):
    pass


@admin.register(Ticket, site=saranalaya_admin_site)
class TicketAdmin(SimpleHistoryAdmin, ModelAdmin):
    list_display = ('title', 'price')
    ordering = ("id",)

    search_fields = ('title', 'description')
    