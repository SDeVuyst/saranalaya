def get_years_from_request(request):
    valid_years = request.GET.getlist('years', [])
    valid_years = [year.replace('/', '') for year in valid_years]

    return valid_years


def get_last_available_adoption_sponsoring_year(parent_sponsors):
    return str(parent_sponsors.latest().date.year)