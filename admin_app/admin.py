from django.contrib import admin
from .models import *



class AdoptionInline(admin.StackedInline):
    model = AdoptionParent.children.through
    verbose_name = "Adoption Parent - Child"
    verbose_name_plural = "Adoption Parents - Children"


class AdoptionParentSponsoringInline(admin.StackedInline):
    model = AdoptionParentSponsoring


@admin.register(AdoptionParent)
class AdoptionParentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'get_children')
    ordering = ('id',)
    inlines = [
        AdoptionInline,
        AdoptionParentSponsoringInline
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'address', 'mail', 'description', 'phone_number', 'children')
    list_filter = ('first_name', 'last_name', 'firm', 'address', 'mail', 'description', 'phone_number', 'children')


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'day_of_birth', 'get_adoption_parents')
    ordering = ('day_of_birth',)
    inlines = [
        AdoptionInline
    ]

    search_fields = ('name', 'gender', 'get_adoption_parents', 'day_of_birth', 'date_of_admission', 'date_of_leave', 'parent_status', 'status', 'link_website', 'description')
    list_filter = ('name', 'gender', 'day_of_birth', 'date_of_admission', 'date_of_leave', 'parent_status', 'status', 'link_website', 'description')

class DonationInline(admin.StackedInline):
    model = Donation


@admin.register(AdoptionParentSponsoring)
class AdoptionParentSponsoringAdmin(admin.ModelAdmin):
    class Media:
        js = ('main.js',)   

    list_display = ('date', 'amount', 'parent', 'get_amount_left')
    ordering = ('date', 'amount')

    search_fields = ('date', 'amount', 'get_amount_left', 'description', 'parent', 'child')
    list_filter = ('date', 'amount', 'description', 'parent', 'child')


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