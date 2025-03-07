from email.utils import formataddr
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import urlencode
from django.core.mail import send_mail
from django.conf import settings
from .models import *
from django.templatetags.static import static
from .utils import helper
from datetime import datetime
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy_
from unfold.contrib.filters.admin import RangeDateFilter, RangeNumericFilter, FieldTextFilter
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.contrib.inlines.admin import StackedInline, TabularInline
from simple_history.admin import SimpleHistoryAdmin
from django import forms
from .sites import saranalaya_admin_site
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from django_celery_beat.admin import ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import CrontabScheduleAdmin as BaseCrontabScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.admin import PeriodicTaskForm, TaskSelectWidget
from unfold.widgets import (
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
)

class NotiModelAdmin(ModelAdmin):
    """Base admin class that captures the request user and sends notifications"""

    def save_model(self, request, obj, form, change):
        """Capture the user making the update and differentiate between create/update"""
        is_new = not change  # True if it's a create, False if it's an update
        super().save_model(request, obj, form, change)
        self.send_model_notifications(obj, request.user, "create" if is_new else "update")

    def send_model_notifications(self, instance, updated_by, action):
        """Send notifications only if the update was made by a watched user"""

        model_name = instance._meta.verbose_name
        try:
            preference = ModelNotificationPreference.objects.get(model_name=model_name)
            print(preference)

            # Check if the updater is in the watched users list
            if updated_by in preference.watched_users.all():
                # Generate the admin URL for the model (only for create & update)
                admin_url = "https://vanakaam.be" + resolve_url(
                    reverse(f"admin:{instance._meta.app_label}_{instance._meta.model_name}_change", args=[instance.pk])
                )
                admin_link = f"\n\nView in admin: {admin_url}"

                # Get all subscriber emails
                recipient_emails = [user.email for user in preference.subscribers.all() if user.email]

                if recipient_emails:
                    action_messages = {
                        "create": f"🆕 {updated_by.username} has created a new {model_name}: {instance}",
                        "update": f"✏️ {updated_by.username} has updated a {model_name}: {instance}",
                    }

                    email_subject = f"{model_name} was {action}d!"
                    email_message = f"{action_messages[action]}{admin_link}"
                    
                    send_mail(
                        subject=email_subject,
                        message=email_message,
                        from_email=formataddr(('Admin | Saranalaya', settings.EMAIL_HOST_USER)),
                        recipient_list=recipient_emails,
                    )

        except ModelNotificationPreference.DoesNotExist as err:
            pass  # No preferences set for this model


# FORMS #
class AdoptionInlineFormChild(forms.ModelForm):
    class Meta:
        model = AdoptionParent.children.through
        fields = ['child', 'active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['child'].queryset = Child.objects.order_by('name')


class AdoptionInlineFormParent(forms.ModelForm):
    class Meta:
        model = AdoptionParent.children.through
        fields = ['adoptionparent', 'active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['adoptionparent'].queryset = AdoptionParent.objects.order_by('first_name')


class AdoptionSponsoringForm(forms.ModelForm):
    class Meta:
        model = AdoptionParentSponsoring
        fields = ['parent', 'child', 'amount', 'date', 'description']

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if 'parent' in self.data:
    #         # only adopted children are available for selection
    #         try:
    #             parent_id = int(self.data.get('parent'))
    #             self.fields['child'].queryset = AdoptionParent.objects.get(id=parent_id).children.all()
    #         except (ValueError, TypeError):
    #             pass  # invalid input from the client; ignore and fallback to empty queryset
    #     elif self.instance.pk:
    #         self.fields['child'].queryset = self.instance.parent.children.all()
        

# FILTERS #
class AmountOfAdoptionParentsFilter(admin.SimpleListFilter):

    title = _('Amount of Adoption Parents')
    parameter_name = _('amount_of_adoption_parents')

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
  


# INLINES #
class AdoptionInlineChild(TabularInline):
    model = AdoptionParent.children.through
    form = AdoptionInlineFormChild
    verbose_name = _("Adoption Parent - Child")
    verbose_name_plural = _("Adoption Parents - Children")


class AdoptionInlineParent(TabularInline):
    model = AdoptionParent.children.through
    form = AdoptionInlineFormParent
    verbose_name = _("Child - Adoption Parent")
    verbose_name_plural = _("Children - Adoption Parents")


class AdoptionParentSponsoringInline(StackedInline):
    model = AdoptionParentSponsoring
    form = AdoptionSponsoringForm
    extra = 1
    ordering = ['-date']


class DonationInline(StackedInline):
    model = Donation
    ordering = ['-date']



# MODELS #

@admin.register(AdoptionParent, site=saranalaya_admin_site)
class AdoptionParentAdmin(SimpleHistoryAdmin, NotiModelAdmin):
    list_display = ('first_name', 'last_name', 'get_children')
    exclude = ('children',)
    ordering = ('first_name', 'last_name')
    inlines = [ 
        AdoptionInlineChild,
        AdoptionParentSponsoringInline
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'street_name', 'address_number', 'bus', 'postcode', 'city', 'country', 'mail', 'description', 'phone_number', 'children__name', 'children__description')
    list_filter = (
        ('active', admin.BooleanFieldListFilter), 
        'country', 
        'children', 
        ('city', FieldTextFilter)
    )

    list_filter_submit = True

    actions = [
        "add_new_sponsoring",
        "generate_address_list",
        "generate_mail_list",
    ]

    @action(description=_('Add New Payment'))
    def add_new_sponsoring(modeladmin, request, queryset):
        amount_of_sponsors_saved = 0
        all_children = Child.objects.all()

        for sponsor in queryset:
            if not sponsor.active:
                continue

            children_of_sponsor = [c for c in all_children if sponsor in c.get_adoption_parents() and sponsor.active]
            
            for child in children_of_sponsor:
                sp = AdoptionParentSponsoring(
                    date=datetime.now(),
                    amount=0, 
                    parent=sponsor,
                    child=child
                )

                sp.save()
                amount_of_sponsors_saved += 1


        return messages.success(request, _(f"Added {amount_of_sponsors_saved} Payments!"))

    @action(description=_("Generate Address List"))
    def generate_address_list(modeladmin, request, queryset):
        return helper.generateAddressList(modeladmin, request, queryset)

    @action(description=_("Generate Mailing List"))
    def generate_mail_list(modeladmin, request, queryset):
        link = helper.generateMailList(modeladmin, request, queryset)
        query_string = urlencode({'emails': link})
        return HttpResponseRedirect(reverse('admin:generate_mailto_link') + '?' + query_string)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request  # Make the request available for instance methods
        return qs
    

@admin.register(Child, site=saranalaya_admin_site)
class ChildAdmin(SimpleHistoryAdmin, NotiModelAdmin):

    list_display = ('display_header', 'status_colored', 'day_of_birth', 'get_adoption_parents_formatted')

    @display(
        description=_lazy_('Status'), 
        label={
            StatusChoices.ACTIVE: "success",
            StatusChoices.LEFT: "danger",
            StatusChoices.SUPPORT: "info",
        },
    )
    def status_colored(self, obj):
        return obj.status, obj.get_status_display()
    
    @display(description=_("Name"), header=True)
    def display_header(self, instance: Child):
        return [
            instance.name,
            None,
            instance.name,
            {
                "path": instance.image.url if instance.image else static("img/kinderen/default.JPG"),
                "height": 30,
                "width": 30,
                "borderless": False,
                "squared": False,
            },
        ]
    
    @action(description=_("Generate Address List"))
    def generate_address_list(modeladmin, request, queryset):
        # Extract unique adoption parents from active adoptions
        active_adoptions = Adoption.objects.filter(child__in=queryset, active=True)
        adoption_parents = AdoptionParent.objects.filter(
            id__in=active_adoptions.values_list("adoptionparent", flat=True).distinct()
        )
        return helper.generateAddressList(modeladmin, request, adoption_parents)


    @action(description=_("Generate Mailing List"))
    def generate_mail_list(modeladmin, request, queryset):
        # Extract unique adoption parents from active adoptions
        active_adoptions = Adoption.objects.filter(child__in=queryset, active=True)
        adoption_parents = AdoptionParent.objects.filter(
            id__in=active_adoptions.values_list("adoptionparent", flat=True).distinct()
        )
        link = helper.generateMailList(modeladmin, request, adoption_parents)
        query_string = urlencode({'emails': link})
        return HttpResponseRedirect(reverse('admin:generate_mailto_link') + '?' + query_string)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request  # Make the request available for instance methods
        return qs
    
    
    ordering = ('name',)
    inlines = [
        AdoptionInlineParent
    ]

    search_fields = ('name', 'adoptionparent__first_name', 'adoptionparent__last_name', 'adoptionparent__firm', 'adoptionparent__description', 'day_of_birth', 'date_of_admission', 'date_of_leave', 'indian_parent_status', 'status', 'website_description', 'description')
    list_filter = (
        AmountOfAdoptionParentsFilter,
        'gender',
        'status',
        'indian_parent_status',
        ('day_of_birth', RangeDateFilter), 
        ('date_of_admission', RangeDateFilter), 
        ('date_of_leave', RangeDateFilter), 
    )

    list_filter_submit = True

    actions = [
        "generate_address_list",
        "generate_mail_list",
    ]


@admin.register(AdoptionParentSponsoring, site=saranalaya_admin_site)
class AdoptionParentSponsoringAdmin(SimpleHistoryAdmin, NotiModelAdmin):
    class Media:
        js = ('js/paymentcolor.js',)   

    form = AdoptionSponsoringForm

    list_display = ('date', 'amount', 'parent', 'child', 'get_amount_left')
    ordering = ('-date', 'amount')

    search_fields = ('date', 'amount', 'description', 'parent__first_name', 'parent__last_name','parent__firm', 'parent__street_name', 'parent__postcode', 'parent__city', 'parent__country', 'parent__mail', 'parent__description', 'parent__phone_number', 'child__name')
    list_filter = (
        ('date', RangeDateFilter), 
        ('amount', RangeNumericFilter), 
        'parent', 'child'
    )

    list_filter_submit = True

    actions = [
        "generate_address_list",
        "generate_mail_list",
        "mark_as_read",
        "mark_as_unread"
    ]

    @action(description=_("Generate Address List"))
    def generate_address_list(modeladmin, request, queryset):
        # queryset should only be the corresponding adoptionparents
        parent_queryset = queryset.values_list('parent', flat=True).distinct()
        parents = AdoptionParent.objects.filter(id__in=parent_queryset)
        return helper.generateAddressList(modeladmin, request, parents)

    @action(description=_("Generate Mailing List"))
    def generate_mail_list(modeladmin, request, queryset):
        # queryset should only be the corresponding adoptionparents
        parent_queryset = queryset.values_list('parent', flat=True).distinct()
        parents = AdoptionParent.objects.filter(id__in=parent_queryset)
        link = helper.generateMailList(modeladmin, request, parents)
        query_string = urlencode({'emails': link})
        return HttpResponseRedirect(reverse('admin:generate_mailto_link') + '?' + query_string)
    
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request  # Make the request available for instance methods
        return qs
    

@admin.register(Sponsor, site=saranalaya_admin_site)
class SponsorAdmin(SimpleHistoryAdmin, NotiModelAdmin):
    list_display = ('first_name', 'last_name', 'letters')
    ordering = ('first_name', 'last_name')
    inlines = [
        DonationInline
    ]

    search_fields = ('first_name', 'last_name', 'firm', 'street_name', 'address_number', 'bus', 'postcode', 'city', 'country', 'mail', 'description', 'phone_number')
    list_filter = (
        'letters', 
        'country', 
        ('city', FieldTextFilter),
    )
    list_filter_submit = True

    actions = [
        "generate_address_list",
        "generate_mail_list",
    ]

    @action(description=_("Generate Address List"))
    def generate_address_list(modeladmin, request, queryset):
        return helper.generateAddressList(modeladmin, request, queryset)

    @action(description=_("Generate Mailing List"))
    def generate_mail_list(modeladmin, request, queryset):
        link = helper.generateMailList(modeladmin, request, queryset)
        query_string = urlencode({'emails': link})
        return HttpResponseRedirect(reverse('admin:generate_mailto_link') + '?' + query_string)
    

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request  # Make the request available for instance methods
        return qs
    

@admin.register(Donation, site=saranalaya_admin_site)
class DonationAdmin(SimpleHistoryAdmin, NotiModelAdmin):
    list_display = ('date', 'amount', 'sponsor')
    ordering = ('-date', 'amount')
    search_fields = ('sponsor__first_name', 'sponsor__last_name', 'sponsor__firm', 'sponsor__street_name', 'sponsor__postcode', 'sponsor__city', 'sponsor__country', 'sponsor__mail', 'sponsor__description', 'sponsor__phone_number', 'amount', 'date', 'description')
    list_filter = (
        ('date' , RangeDateFilter),
        ('amount', RangeNumericFilter),
        'sponsor'
    )
    list_filter_submit = True    

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request  # Make the request available for instance methods
        return qs


@admin.register(ModelNotificationPreference, site=saranalaya_admin_site)
class ModelNotificationPreferenceAdmin(ModelAdmin):
    list_display = ("model_name",)  
    filter_horizontal = ("subscribers", "watched_users")  # Allows selecting multiple users


@admin.register(News, site=saranalaya_admin_site)
class NewsAdmin(SimpleHistoryAdmin, NotiModelAdmin):
    list_display = ('display_header', 'date', 'show_on_website')
    search_fields = ('title', 'content')

    @display(description=_("Title"), header=True)
    def display_header(self, instance: News):
        return [
            instance.title,
            None,
            instance.title,
            {
                "path": instance.image.url,
                "height": 24,
                "width": 24,
                "borderless": True,
                "squared": True,
            },
        ]
    

# CELERY #

admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)


class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    pass


class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldAdminTextInputWidget()
        self.fields["regtask"].widget = UnfoldTaskSelectWidget()


@admin.register(PeriodicTask, site=saranalaya_admin_site)
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule, site=saranalaya_admin_site)
class IntervalScheduleAdmin(ModelAdmin):
    pass


@admin.register(CrontabSchedule, site=saranalaya_admin_site)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, ModelAdmin):
    pass


@admin.register(ClockedSchedule, site=saranalaya_admin_site)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, ModelAdmin):
    pass