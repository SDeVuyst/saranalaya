from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import FileResponse


def get_years_from_request(request):
    valid_years = request.GET.getlist('years', [])
    valid_years = [year.replace('/', '') for year in valid_years]

    return valid_years


def get_last_available_adoption_sponsoring_year(parent_sponsors):
    return str(parent_sponsors.latest().date.year)


# mailing and adress list
def generateMailList(modeladmin, request, queryset):
    response = FileResponse(
        generateMailListFile(queryset), 
        as_attachment=True, 
        filename='mail_list.pdf'
    )
    return response


def generateMailListFile(queryset):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
 
    # Create a PDF document
    supporters = queryset.all()
 
    y = 790
    for supporter in supporters:
        p.drawString(50, y, supporter.mail)
        y -= 15

    p.showPage()
    p.save()
 
    buffer.seek(0)
    return buffer


def generateAddressList(modeladmin, request, queryset):
    response = FileResponse(generateAddressListFile(queryset), 
                            as_attachment=True, 
                            filename='address_list.pdf')
    return response


def generateAddressListFile(queryset):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
 
    # Create a PDF document
    supporters = queryset.all()
 
    y = 790
    for supporter in supporters:
        p.drawString(50, y, f"{supporter.first_name} {supporter.last_name}")
        p.drawString(50, y - 20, f"{supporter.street_name} {supporter.address_number} {supporter.bus if supporter.bus is not None else ''}")
        p.drawString(50, y - 40, f"{supporter.postcode} {supporter.city}")
        p.drawString(50, y - 60, supporter.country)
        y -= 100
 
    p.showPage()
    p.save()
 
    buffer.seek(0)
    return buffer


def percentage_change(a, b):
    return (b - a) / a * 100