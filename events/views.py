from .models import Event, Ticket
from django.shortcuts import get_object_or_404, get_list_or_404, render 

def eventpage(request, id):
    event = get_object_or_404(Event, pk=id)
    tickets = get_list_or_404(Ticket, pk=event.id)

    context = {
        'event': event,
        'tickets': tickets
    }

    return render(request, 'event.html', context)
