from datetime import datetime
from email.utils import formataddr
from celery import shared_task 
from django.conf import settings
from django.core.mail import send_mail
from .models import AdoptionParent, AdoptionParentSponsoring, Child, User
from .utils import utils


@shared_task
def notification_mail(user_id):

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return "User not found!"
    
    # get user notifications
    child_noti = utils.child_badge_callback(user)
    adoptionparent_noti = utils.adoptionparent_badge_callback(user)
    payment_noti = utils.payment_badge_callback(user)
    sponsor_noti = utils.sponsor_badge_callback(user)
    donation_noti = utils.donation_badge_callback(user)
    
    # no notifications
    if all(var == "" for var in [child_noti, adoptionparent_noti, payment_noti, sponsor_noti, donation_noti]):
        return f"No notifications for {user.username}"
    
    # Construct email body
    message_lines = [f"Beste {user.username},\n\nJe hebt de volgende ongelezen meldingen:"]
    
    if child_noti:
        message_lines.append(f"- Kind meldingen: {child_noti}")
    if adoptionparent_noti:
        message_lines.append(f"- Adoptie-ouder meldingen: {adoptionparent_noti}")
    if payment_noti:
        message_lines.append(f"- Adoptie-ouder Betaling meldingen: {payment_noti}")
    if sponsor_noti:
        message_lines.append(f"- Sponsor meldingen: {sponsor_noti}")
    if donation_noti:
        message_lines.append(f"- Donatie meldingen: {donation_noti}")

    message = "\n".join(message_lines) + "\n\nBekijk ze via vanakaam.be/admin"
    
    send_mail(
        'Je hebt ongelezen meldingen!',
        message,
        formataddr(('Admin | Saranalaya', settings.EMAIL_HOST_USER)),
        [user.email],
        fail_silently=False,
    )

    return f"notification email sent to {user.username}"


@shared_task
def add_yearly_adoption_parent_payments():
    amount_of_sponsors_saved = 0
    all_children = Child.objects.all()

    for sponsor in AdoptionParent.objects.all():
        if not sponsor.active:
            continue
        
        children_of_sponsor = [c for c in all_children if sponsor in c.get_adoption_parents()]
        
        for child in children_of_sponsor:
            sp = AdoptionParentSponsoring(
                date=datetime.now(),
                amount=0, 
                parent=sponsor,
                child=child
            )

            sp.save()
            amount_of_sponsors_saved += 1

    return f"{amount_of_sponsors_saved} payments added"