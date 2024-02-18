from django.contrib import admin
from .models import *
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import SimpleListFilter
from rangefilter.filters import (
    DateRangeFilterBuilder,
    NumericRangeFilterBuilder,
)



def generateMailList(modeladmin, request, queryset):
    response = FileResponse(generateMailListFile(queryset), 
                            as_attachment=True, 
                            filename='mail_list.pdf')
    return response

generateMailList.short_description = 'Generate Mail List'


def generateMailListFile(queryset):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
 
    # Create a PDF document
    supporters = queryset.all()
 
    y = 790
    for supporter in supporters:
        p.drawString(50, y, supporter.mail)
        y -= 15

    p.showPage()
    p.save()
 
    buffer.seek(0)
    return buffer


def generateAddressList(modeladmin, request, queryset):
    response = FileResponse(generateAddressListFile(queryset), 
                            as_attachment=True, 
                            filename='address_list.pdf')
    return response

generateAddressList.short_description = 'Generate Address List'

def generateAddressListFile(queryset):
    from io import BytesIO
    from reportlab.pdfgen import canvas
 
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
 
    # Create a PDF document
    supporters = queryset.all()
 
    y = 790
    for supporter in supporters:
        p.drawString(50, y, f"{supporter.first_name} {supporter.last_name}")
        p.drawString(50, y - 20, f"{supporter.street_name} {supporter.address_number} {supporter.bus if supporter.bus is not None else ''}")
        p.drawString(50, y - 40, f"{supporter.postcode} {supporter.city}")
        p.drawString(50, y - 60, supporter.country)
        y -= 100
 
    p.showPage()
    p.save()
 
    buffer.seek(0)
    return buffer



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
    actions = [
        generateAddressList,
        generateMailList
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'street_name', 'address_number', 'bus', 'postcode', 'city', 'country', 'mail', 'description', 'phone_number', 'children')
    list_filter = ('postcode', 'city', 'country', 'children')

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'day_of_birth', 'get_adoption_parents')
    ordering = ('day_of_birth',)
    inlines = [
        AdoptionInline
    ]

    search_fields = ('name', 'gender', 'get_adoption_parents', 'day_of_birth', 'date_of_admission', 'date_of_leave', 'parent_status', 'status', 'link_website', 'description')
    list_filter = (
        'gender',
        ('day_of_birth', DateRangeFilterBuilder(title="By Day of Birth")), 
        ('date_of_admission', DateRangeFilterBuilder(title="By Date of Admission")), 
        ('date_of_leave', DateRangeFilterBuilder(title="By Day of Leave")), 
        'parent_status', 'status',)


class DonationInline(admin.StackedInline):
    model = Donation


@admin.register(AdoptionParentSponsoring)
class AdoptionParentSponsoringAdmin(admin.ModelAdmin):
    class Media:
        js = ('main.js',)   

    list_display = ('date', 'amount', 'parent', 'get_amount_left')
    ordering = ('date', 'amount')

    search_fields = ('date', 'amount', 'get_amount_left', 'description', 'parent', 'child')
    list_filter = (
        ('date', DateRangeFilterBuilder(title="By Date")), 
        ('amount', NumericRangeFilterBuilder(title="By Amount")), 
        'parent', 'child'
    )


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', )
    ordering = ('id',)
    inlines = [
        DonationInline
    ]
    actions = [
        generateAddressList,
        generateMailList
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'street_name', 'address_number', 'bus', 'postcode', 'city', 'country', 'mail', 'description', 'phone_number')
    list_filter = ('postcode', 'city', 'country')

    


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'sponsor')
    ordering = ('date', 'amount')
    search_fields = ('sponsor', 'amount', 'date', 'description')
    list_filter = (
        'sponsor',
        ('amount', NumericRangeFilterBuilder(title="By Amount")), 
        ('date' , DateRangeFilterBuilder(title="By Date")),
    )