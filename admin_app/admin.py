from django.contrib import admin, messages
from .models import *
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from rangefilter.filters import (
    DateRangeFilterBuilder,
    NumericRangeFilterBuilder,
)


class AmountOfAdoptionParentsFilter(admin.SimpleListFilter):

    title = 'Amount of Adoption Parents'
    parameter_name = 'amount_of_adoption_parents'

    def lookups(self, request, model_admin):
        return [
            ("0", _("No Adoption Parents")),
            ("1", _("1 Adoption Parent")),
            ("2", _("2 Adoption Parents")),
            ("3", _("3 Adoption Parents")),
            ("3+", _("More than 3 Adoption Parents")),
        ]

    def queryset(self, request, queryset):
        
        ap_count = {}
        for ap in AdoptionParent.objects.all():
            children = ap.children.all()

            for child in children:
                if child in ap_count:
                    ap_count[child] += 1
                else:
                    ap_count[child] = 1

        if self.value() == "0":
            all_children = list(Child.objects.all())
            children_with_ap = [ch[0] for ch in ap_count.items()]
            # remaining_children = all_children.difference(children_with_ap)
            set_difference = set(all_children) - set(children_with_ap)
            remaining_children = list(set_difference)

            correct_ch = [ch.pk for ch in remaining_children]
            return queryset.filter(
                id__in=correct_ch
            )
        
        elif self.value() == "1":
            correct_aps = list(filter(
                lambda a: a[1] == 1,
                ap_count.items(),
            ))
            correct_aps = [ch[0].pk for ch in correct_aps]
            return queryset.filter(
                id__in=correct_aps
            )
        
        elif self.value() == "2":
            correct_aps = list(filter(
                lambda a: a[1] == 2,
                ap_count.items(),
            ))
            correct_aps = [ch[0].pk for ch in correct_aps]
            return queryset.filter(
                id__in=correct_aps
            )
        
        elif self.value() == "3":
            correct_aps = list(filter(
                lambda a: a[1] == 3,
                ap_count.items(),
            ))
            correct_aps = [ch[0].pk for ch in correct_aps]
            return queryset.filter(
                id__in=correct_aps
            )

        elif self.value() == "3+":
            correct_aps = list(filter(
                lambda a: a[1] > 3,
                ap_count.items(),
            ))
            correct_aps = [ch[0].pk for ch in correct_aps]
            return queryset.filter(
                id__in=correct_aps
            )
        

        return queryset
        
        

def addNewSponsoring(modeladmin, request, queryset):
    amount_of_sponsors_saved = 0

    for sponsor in queryset:
        if not sponsor.active:
            continue

        children_of_sponsor = [c for c in Child.objects.all() if sponsor in c.get_adoption_parents()]
         
        for child in children_of_sponsor:
            sp = AdoptionParentSponsoring(
                date=datetime.now(),
                amount=0, 
                parent=sponsor,
                child=child
            )

            sp.save()
            amount_of_sponsors_saved += 1


    return messages.success(request, f"Added {amount_of_sponsors_saved} Payments!")

addNewSponsoring.short_description = 'Add New Payment'



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
    exclude = ('children',)
    ordering = ('id',)
    inlines = [
        AdoptionInline,
        AdoptionParentSponsoringInline
    ]
    actions = [
        generateAddressList,
        generateMailList,
        addNewSponsoring
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'street_name', 'address_number', 'bus', 'postcode', 'city', 'country', 'mail', 'description', 'phone_number', 'children__name', 'children__description')
    list_filter = ('postcode', 'city', 'country', 'children', ('active', admin.BooleanFieldListFilter))


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('name', 'day_of_birth', 'get_adoption_parents_formatted')
    ordering = ('day_of_birth',)
    inlines = [
        AdoptionInline
    ]

    search_fields = ('name', 'gender', 'adoptionparent__first_name', 'adoptionparent__last_name', 'adoptionparent__firm', 'adoptionparent__street_name', 'adoptionparent__postcode', 'adoptionparent__city', 'adoptionparent__country', 'adoptionparent__mail', 'adoptionparent__description', 'adoptionparent__phone_number', 'day_of_birth', 'date_of_admission', 'date_of_leave', 'indian_parent_status', 'status', 'link_website', 'description')
    list_filter = (
        AmountOfAdoptionParentsFilter,
        'gender',
        ('day_of_birth', DateRangeFilterBuilder(title="By Day of Birth")), 
        ('date_of_admission', DateRangeFilterBuilder(title="By Date of Admission")), 
        ('date_of_leave', DateRangeFilterBuilder(title="By Day of Leave")), 
        'indian_parent_status', 'status'
    )


class DonationInline(admin.StackedInline):
    model = Donation


@admin.register(AdoptionParentSponsoring)
class AdoptionParentSponsoringAdmin(admin.ModelAdmin):
    class Media:
        js = ('main.js',)   

    list_display = ('date', 'amount', 'parent', 'child', 'get_amount_left')
    ordering = ('date', 'amount')

    search_fields = ('date', 'amount', 'description', 'parent__first_name', 'parent__last_name','parent__firm', 'parent__street_name', 'parent__postcode', 'parent__city', 'parent__country', 'parent__mail', 'parent__description', 'parent__phone_number', 'child__name')
    list_filter = (
        ('date', DateRangeFilterBuilder(title="By Date")), 
        ('amount', NumericRangeFilterBuilder(title="By Amount")), 
        'parent', 'child'
    )


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'letters')
    ordering = ('id',)
    inlines = [
        DonationInline
    ]
    actions = [
        generateAddressList,
        generateMailList
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'street_name', 'address_number', 'bus', 'postcode', 'city', 'country', 'mail', 'description', 'phone_number')
    list_filter = ('postcode', 'city', 'country', 'letters')

    


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'sponsor')
    ordering = ('date', 'amount')
    search_fields = ('sponsor__first_name', 'sponsor__last_name', 'sponsor__firm', 'sponsor__street_name', 'sponsor__postcode', 'sponsor__city', 'sponsor__country', 'sponsor__mail', 'sponsor__description', 'sponsor__phone_number', 'amount', 'date', 'description')
    list_filter = (
        'sponsor',
        ('amount', NumericRangeFilterBuilder(title="By Amount")), 
        ('date' , DateRangeFilterBuilder(title="By Date")),
    )