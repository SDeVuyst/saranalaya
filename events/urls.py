from django.urls import path
from . import views

urlpatterns = [
    path('<int:id>/', views.eventpage, name="eventpage"),
    path('koop-ticket/<int:event_id>/', views.buy_ticket, name="buyticket"),
    
    path("ticket/<int:payment_id>/success/", views.payment_success),

    path("set-attendance/", views.set_attendance),
    path("scanner/", views.scanner),

    path("beleid/", views.beleid),

    path("mollie-webhook/", views.mollie_webhook)
]