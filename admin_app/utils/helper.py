from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import FileResponse
from PyPDF2 import PdfWriter, PdfReader

def get_years_from_request(request):
    valid_years = request.GET.getlist('years', [])
    valid_years = [year.replace('/', '') for year in valid_years]

    return valid_years


def get_last_available_adoption_sponsoring_year(parent_sponsors):
    return str(parent_sponsors.latest().date.year)


# mailing and adress list
def generateMailList(modeladmin, request, queryset):
    supporters = queryset.all()
    return ','.join([sup.mail for sup in supporters if sup.mail])


def generateAddressList(modeladmin, request, queryset):
    buffers = []
    # split queryset into chunks of 8
    # its possible that queryset is not divisible by 8
    # so we need to handle the last chunk separately
    chunks, chunk_size = len(queryset) // 8, 8
    for i in range(chunks):
        chunk = queryset[i * chunk_size:(i + 1) * chunk_size]
        buffers.append(generateAddressListFile(chunk))
    if len(queryset) % 8 != 0:
        chunk = queryset[chunks * chunk_size:]
        buffers.append(generateAddressListFile(chunk))

    merged_pdf = mergeBuffersIntoPdf(buffers)

    response = FileResponse(merged_pdf, 
                            as_attachment=True, 
                            filename='address_list.pdf')
    return response


def generateAddressListFile(supporters):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
  
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
    if a == 0: return -100
    return (b - a) / a * 100


def mergeBuffersIntoPdf(buffers):
    # Use PyPDF2 to merge buffers
    writer = PdfWriter()

    for buffer in buffers:
        reader = PdfReader(buffer)
        for page in reader.pages:
            writer.add_page(page)

    # Output the merged PDF into a new buffer
    merged_buffer = BytesIO()
    writer.write(merged_buffer)
    merged_buffer.seek(0)
    return merged_buffer