import django_filters
from django import forms
from .models import Child, GenderChoices, StatusChoices

class KindFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr='icontains',
        label="Naam",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name'})
    )
    gender = django_filters.ChoiceFilter(
        choices=GenderChoices.choices,
        label="Gender",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = django_filters.ChoiceFilter(
        choices=StatusChoices.choices,
        label="Status",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_admission = django_filters.DateFilter(
        lookup_expr='gte',
        label="Opgenomen Na",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    day_of_birth__gte = django_filters.DateFilter(
        field_name='day_of_birth',
        lookup_expr='gte',
        label="Geboren Na",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    day_of_birth__lte = django_filters.DateFilter(
        field_name='day_of_birth',
        lookup_expr='lte',
        label="Geboren Voor",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = Child
        fields = ['name', 'gender', 'status', 'date_of_admission', 'day_of_birth__gte', 'day_of_birth__lte']
