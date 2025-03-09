from django.apps import apps
from django.db import models
from django.contrib import admin
from django.utils.html import format_html
from django.shortcuts import resolve_url
from django.contrib.auth import get_user_model
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from simple_history.models import HistoricalRecords
from ckeditor.fields import RichTextField
from django.urls import path, reverse
from .utils.helper import generate_mailto_link
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from .sites import saranalaya_admin_site

import os


# Unfold model admin
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User, site=saranalaya_admin_site)
class UserAdmin(BaseUserAdmin, ModelAdmin):

    actions = ["generate_mail_list"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('generate_mailto_link/', generate_mailto_link, name='generate_mailto_link'),
        ]
        return custom_urls + urls


@admin.register(Group, site=saranalaya_admin_site)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass

# CHOICES #

class GenderChoices(models.TextChoices):
    MALE = 'm', _('Male')
    FEMALE = 'f', _('Female')


class ParentStatusChoices(models.TextChoices):
    NONE = 'n', _('No Parents')
    ONE = 'o', _('One Parent')
    TWO = 't', _('Two Parents')


class StatusChoices(models.TextChoices):
    ACTIVE = 'a', _('Active')
    LEFT = 'l', _('Left')
    SUPPORT = 's', _('Support')


class ModelChoices(models.TextChoices):
    CHILD = 'Child', _('Child')
    ADOPTIONPARENT = 'Adoption Parent', _('Adoption Parent')
    ADOPTION = 'Adoption', _('Adoption')
    ADOPTIONPARENTSPONSORING = 'Adoption Parent Payment', _('Adoption Parent Payment')
    SPONSOR = 'Sponsor', _('Sponsor')
    DONATION = 'Donation', _('Donation')


# MODELS #
class Child(models.Model):
    class Meta:
        verbose_name = _("Child")
        verbose_name_plural = _("Children")
        ordering = ["name", "day_of_birth"]

    def __str__(self) -> str:
        return self.name
    
    def get_absolute_url(self):
        return reverse("child_detail", kwargs={"id": self.id})
    
    
    @admin.display(description=_('Adoption Parents'))
    def get_adoption_parents_formatted(self):
        formatted_list = []
        for adoption in Adoption.objects.filter(child_id=self.pk):
            url = resolve_url(admin_urlname(AdoptionParent._meta, 'change'), adoption.adoptionparent.id)
            formatted_list.append(format_html(
                f'<a class="{"bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400 leading-normal py-1 px-1 rounded" if not adoption.active else ""}" href="{url}">{str(adoption.adoptionparent.first_name + " " + adoption.adoptionparent.last_name)}</a>'
            ))

        return format_html(", ".join(formatted_list))

    def get_adoption_parents(self):
        return self.adoptionparent_set.all()


    name = models.CharField(max_length=60, verbose_name=_("name"))
    gender = models.CharField(max_length = 1, choices = GenderChoices.choices, verbose_name=_("gender"))
    day_of_birth = models.DateField(verbose_name=_("Day of Birth"))
    date_of_admission = models.DateField(verbose_name=_("Date of Admission"))
    date_of_leave = models.DateField(blank=True, null=True, verbose_name=_("Date of Leave"))
    indian_parent_status = models.CharField(max_length = 1, choices = ParentStatusChoices.choices, verbose_name=_("Indian Parent Status"))
    status = models.CharField( max_length = 1, choices = StatusChoices.choices, verbose_name=_("Status"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    show_on_website = models.BooleanField(default=False, verbose_name=_("Show on Website"))
    image = models.ImageField(upload_to='children/', blank=True, null=True, verbose_name=_("Image"))
    website_description = RichTextField(blank=True, null=True, verbose_name=_("Website Description"))
    last_updated = models.DateTimeField(auto_now=True)

    history = HistoricalRecords(verbose_name=_("History"))


class Supporter(models.Model):
    class Meta:
        abstract = True
        ordering = ['first_name', 'last_name']
        verbose_name = _("Supporter")
        verbose_name_plural = _("Supporters")

    def __str__(self) -> str:
        return self.first_name + ' ' + self.last_name

    first_name = models.CharField(max_length=50, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=50, verbose_name=_("Last Name"))
    firm = models.CharField(max_length=45, blank=True, null=True, verbose_name=_("Firm")) # not required
    street_name = models.CharField(max_length=100, verbose_name=_("Street Name"))
    address_number = models.IntegerField(verbose_name=_("Address Number"))
    bus = models.CharField(max_length=15, blank=True, null=True, verbose_name=_("Bus"))
    postcode = models.CharField(max_length=15, verbose_name=_("Postcode"))
    city = models.CharField(max_length=40, verbose_name=_("City"))
    country = models.CharField(max_length=40, default="Belgium", verbose_name=_("Country"))
    mail = models.EmailField(verbose_name=_("E-mail"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    phone_number = models.CharField(max_length=12, blank=True, null=True, verbose_name=_("Phone Number")) # not required
    last_updated = models.DateTimeField(auto_now=True)


class AdoptionParent(Supporter):
    class Meta(Supporter.Meta):
        verbose_name = _("Adoption Parent")
        verbose_name_plural = _("Adoption Parents")

    @admin.display(description=_('Children'))
    def get_children(self):
        formatted_list = []
        for adoption in Adoption.objects.filter(adoptionparent_id=self.pk):
            url = resolve_url(admin_urlname(Child._meta, 'change'), adoption.child.id)
            formatted_list.append(format_html(
                f'<a class="{"bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400 leading-normal py-1 px-1 rounded" if not adoption.active else ""}"href="{url}">{str(adoption.child.name)}</a>'
            ))

        return format_html(", ".join(formatted_list))
    

    children = models.ManyToManyField("Child", through="Adoption", blank=True, verbose_name=_("Children"))
    active = models.BooleanField(default=True, verbose_name=_("Active"))

    history = HistoricalRecords(verbose_name=_("History"))

    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = self.__class__.objects.get(pk=self.pk)
            if old_instance.active and not self.active:
                # Set all adoptions to inactive if parent is set to inactive
                Adoption.objects.filter(adoptionparent_id=self.pk).update(active=False)

        super().save(*args, **kwargs)


class Adoption(models.Model):
    class Meta:
        verbose_name = _("Adoption")
        verbose_name_plural = _("Adoptions")

    adoptionparent = models.ForeignKey(AdoptionParent, on_delete=models.CASCADE)
    child = models.ForeignKey(Child, on_delete=models.CASCADE)

    active = models.BooleanField(verbose_name=_("Active"), default=True)


class AdoptionParentSponsoring(models.Model):
    class Meta:
        verbose_name = _("Adoption Parent Payment")
        verbose_name_plural = _("Adoption Parent Payments")
        get_latest_by = "date"

    def __str__(self) -> str:
        return str(self.parent) + f" ({str(self.date)})" + " - " + str(self.amount) + "/186"

    @property
    @admin.display(description=_("Amount remaining"))
    def get_amount_left(self):
        return max(0, float(os.environ.get("AMOUNT_ADOPTION_PARENTS")) - self.amount)
    

    def is_enough(self):
        return int(os.environ.get("AMOUNT_ADOPTION_PARENTS")) <= self.amount

    date = models.DateField(verbose_name=_("Date"))
    amount = models.FloatField(verbose_name=_("Amount"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    parent = models.ForeignKey(AdoptionParent, on_delete=models.RESTRICT, verbose_name=_("Parent"))
    child = models.ForeignKey(Child, on_delete=models.RESTRICT, verbose_name=_("Child"))
    last_updated = models.DateTimeField(auto_now=True)

    history = HistoricalRecords(verbose_name=_("History"))

    
class Sponsor(Supporter):
    class Meta(Supporter.Meta):
        verbose_name = _("Sponsor")
        verbose_name_plural = _("Sponsors")

    letters = models.BooleanField(default=True, verbose_name=_("Letters"))
    
    history = HistoricalRecords(verbose_name=_("History"))


class Donation(models.Model):
    class Meta:
        verbose_name = _("Donation")
        verbose_name_plural = _("Donations")

    def __str__(self) -> str:
        return str(self.sponsor) + f" ({str(self.date)})" + ' - ' + str(self.amount)

    sponsor = models.ForeignKey(Sponsor, on_delete=models.RESTRICT, verbose_name=_("Sponsor"))
    amount = models.FloatField(verbose_name=_("Amount"))
    date = models.DateField(verbose_name=_("Date"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    last_updated = models.DateTimeField(auto_now=True)

    history = HistoricalRecords(verbose_name=_("History"))

class News(models.Model):
    class Meta:
        verbose_name = _("News")
        verbose_name_plural = _("News")
        ordering = ["-date"]

    def __str__(self) -> str:
        return self.title
    
    def get_absolute_url(self):
        return reverse("news_detail", kwargs={"id": self.id})

    title = models.CharField(max_length=100, verbose_name=_("Title"))
    content = RichTextField(verbose_name=_("Content"))
    date = models.DateField(default=now, verbose_name=_("Date"))
    image = models.ImageField(upload_to='news/', verbose_name=_("Image"))
    last_updated = models.DateTimeField(auto_now=True)
    show_on_website = models.BooleanField(default=True, verbose_name=_("Show on Website"))

    history = HistoricalRecords(verbose_name=_("History"))


User = get_user_model()

class ModelNotificationPreference(models.Model):
    model_name = models.CharField(max_length=32, choices=ModelChoices.choices, verbose_name=_("Model"))
    subscribers = models.ManyToManyField(User, related_name="receiving_notifications", blank=True)
    watched_users = models.ManyToManyField(User, related_name="triggering_notifications", blank=True)

    def __str__(self):
        return f"Notifications for {self.model_name}"
    