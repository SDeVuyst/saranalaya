from django.urls import path
from admin_app import views

urlpatterns = [
    path("chart/filter-options/", views.get_filter_options, name="chart-filter-options"),
    path("chart/donations-per-year/", views.donations_per_year_chart, name="chart-donations-per-year"),
]