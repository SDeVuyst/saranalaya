from django import template
from django.utils import timezone
import datetime
import pytz

register = template.Library()

@register.filter
def age(birthdate):
    if not isinstance(birthdate, datetime.date):
        return birthdate  # Fallback if something invalid is passed

    today = datetime.date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

    return age