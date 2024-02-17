from django.contrib import admin
from .models import *


@admin.register(AdoptionParent)
class AdoptionParentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', )
    ordering = ('id',)



@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'day_of_birth',)
    ordering = ('day_of_birth',)


class DonationInline(admin.StackedInline):
    model = Donation


@admin.register(AdoptionParentSponsoring)
class AdoptionParentSponsoringAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'get_amount_left')
    ordering = ('date', 'amount')


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', )
    ordering = ('id',)
    inlines = [
        DonationInline
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'address', 'mail', 'description', 'phone_number')
    list_filter = ('first_name', 'last_name', 'firm', 'address', 'mail', 'description', 'phone_number')


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'sponsor')
    ordering = ('date', 'amount')
    search_fields = ('sponsor', 'amount', 'date', 'description')
    list_filter = ('sponsor', 'amount', 'date', 'description')