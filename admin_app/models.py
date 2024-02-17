from django.db import models
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class Supporter(models.Model):
    class Meta:
        abstract = True
        ordering = ['last_name']
        verbose_name = "Supporter"
        verbose_name_plural = "Supporters"

    def __str__(self) -> str:
        return self.first_name + self.last_name

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    firm = models.CharField(max_length=45, blank=True) # not required
    address = models.CharField(max_length=100)
    mail = models.EmailField()
    description = models.TextField(blank=True)



class AdoptionParent(Supporter):
    class Meta(Supporter.Meta):
        verbose_name = "Adoption Parent"
        verbose_name_plural = "Adoption Parents"
    
    phone_number = models.CharField(max_length=12)
    children = models.ManyToManyField("Child", )


class Sponsor(Supporter):
    class Meta(Supporter.Meta):
        verbose_name = "Sponsor"
        verbose_name_plural = "Sponsors"
    
    phone_number = models.CharField(max_length=12, blank=True) # not required


class Child(models.Model):
    class Meta:
        verbose_name = "Child"
        verbose_name_plural = "Children"

    def __str__(self) -> str:
        return self.name
    

    @admin.display(description="Adoption Parents")
    @admin.action()
    def get_parents(self):
        return ""

    name = models.CharField(max_length=60)

    class GenderChoices(models.TextChoices):
        MALE = 'm', _('Male')
        FEMALE = 'f', _('Female')

    gender = models.CharField(
        max_length = 1,
        choices = GenderChoices.choices,
    )
    day_of_birth = models.DateField()
    date_of_admission = models.DateField()
    date_of_leave = models.DateField(blank=True)

    class ParentStatusChoices(models.TextChoices):
        NONE = 'n', _('No Parents')
        ONE = 'o', _('One Parent')
        TWO = 't', _('Two Parents')

    parent_status = models.CharField(
        max_length = 1,
        choices = ParentStatusChoices.choices,
    )

    class StatusChoices(models.TextChoices):
        ACTIVE = 'a', _('Active')
        LEFT = 'l', _('Left')
        SUPPORT = 's', _('Support')

    status = models.CharField(
        max_length = 1,
        choices = StatusChoices.choices,
    )
    link_website = models.URLField(blank=True)
    description = models.TextField(blank=True)



class Donation(models.Model):
    class Meta:
        verbose_name = "Donation"
        verbose_name_plural = "Donations"

    sponsor = models.ForeignKey(Sponsor, on_delete=models.RESTRICT)
    amount = models.FloatField()
    date = models.DateField()
    description = models.TextField(blank=True)


class AdoptionParentSponsoring(models.Model):
    class Meta:
        verbose_name = "Adoption Parent Sponsoring"
        verbose_name_plural = "Adoption Parent Sponsorings"

    @admin.display(description="Amount remaining")
    def get_amount_left(self):
        return float(186) - self.amount

    date = models.DateField()
    amount = models.FloatField()
    description = models.TextField(blank=True)

    parent = models.ForeignKey(AdoptionParent, on_delete=models.RESTRICT)
    child = models.ForeignKey(Child, on_delete=models.RESTRICT)

    