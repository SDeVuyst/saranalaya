from django.urls import path, include
from . import views
from admin_app.sites import saranalaya_admin_site

app_name = 'events'

urlpatterns = [
    path('', views.redirect_to_latest_event, name="index"),
    path('events/<int:id>/', views.eventpage, name="eventpage"),
    path('koop-ticket/<int:event_id>/', views.buy_ticket, name="buyticket"),
    
    path("ticket/<int:payment_id>/success/", views.payment_success),

    path("set-attendance/", views.set_attendance),
    path("scanner/", views.scanner),

    path("beleid/", views.beleid),

    path("mollie-webhook/", views.mollie_webhook),
    path('admin/', views.redirect_to_care, name="admin"),
]