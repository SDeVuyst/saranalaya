from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('kinderen/', views.kinderen, name="kinderen"),
    path('nieuws/', views.nieuws, name="nieuws"),
]