from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('kinderen/', views.kinderen, name="kinderen"),
    path('kinderen/<int:id>/', views.kind_detail, name="kind_detail"),
    path('steun-ons/', views.steun_ons, name="steun-ons"),
    path('nieuws/', views.nieuws, name="nieuws"),
]