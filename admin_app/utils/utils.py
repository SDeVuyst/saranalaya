from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..models import *


def badge_callback(request, model) -> str:
    user = request.user

    # Ensure we have a valid user
    if not user.is_authenticated:
        return ""

    # Get all UserView objects for the current user
    user_views = UserView.objects.filter(
        user=user,
        content_type=ContentType.objects.get_for_model(model)
    )

    all_objects = model.objects.all()

    amount_of_read_objects = 0

    # Filter out objects where last_updated is later than last_viewed for each content_object_id
    for user_view in user_views:
        amount_of_read_objects += all_objects.filter(
            id=user_view.object_id,
            last_updated__lte=user_view.last_viewed
        ).count()

    amount_unread = all_objects.count() - amount_of_read_objects
    return f"{amount_unread}" if amount_unread > 0 else ""



def child_badge_callback(request) -> str:
    return badge_callback(request, Child)

def adoptionparent_badge_callback(request) -> str:
    return badge_callback(request, AdoptionParent)

def payment_badge_callback(request) -> str:
    return badge_callback(request, AdoptionParentSponsoring)

def sponsor_badge_callback(request) -> str:
    return badge_callback(request, Sponsor)

def donation_badge_callback(request) -> str:
    return badge_callback(request, Donation)