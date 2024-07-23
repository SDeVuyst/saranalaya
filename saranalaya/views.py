from django.shortcuts import redirect
from events.models import Event

def redirect_to_admin(request):
    return redirect('/admin/')

def redirect_to_latest_event(request):
    event = Event.objects.latest()
    return redirect(f"/events/{event.id}/")