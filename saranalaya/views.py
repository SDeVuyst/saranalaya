from django.shortcuts import redirect
from events.models import Event

def redirect_to_admin(request):
    return redirect('/admin/')