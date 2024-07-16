from django.urls import path
from . import views

urlpatterns = [
    path('<int:id>/', views.eventpage, name="eventpage"),
    path('koop-ticket/<int:event_id>/', views.buy_ticket, name="buyticket"),
    path("payment-details/<int:payment_id>", views.payment_details),
    path("ticket/<int:payment_id>/success", views.payment_success),
    path("ticket/<int:payment_id>/failure", views.payment_failure,),
]