from datetime import datetime
from email.utils import formataddr
from celery import shared_task 
from django.conf import settings
from django.core.mail import send_mail
from .models import AdoptionParent, AdoptionParentSponsoring, Child, User, StatusChoices


@shared_task
def add_yearly_adoption_parent_payments():
    amount_of_sponsors_saved = 0
    all_children = Child.objects.all()

    for sponsor in AdoptionParent.objects.all():
        if not sponsor.active:
            continue
        
        children_of_sponsor = [c for c in all_children if sponsor in c.get_adoption_parents() and sponsor.active]
        
        for child in children_of_sponsor:
            if child.status != StatusChoices.ACTIVE:
                continue

            sp = AdoptionParentSponsoring(
                date=datetime.now(),
                amount=0, 
                parent=sponsor,
                child=child
            )

            sp.save()
            amount_of_sponsors_saved += 1

    return f"{amount_of_sponsors_saved} payments added"