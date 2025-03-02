from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import FileResponse, HttpResponse
from PyPDF2 import PdfWriter, PdfReader
from django.utils.html import escape

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


def generate_mailto_link(request):
    # Get email addresses from the query parameters
    email_addresses = request.GET.get('emails', '')
    
    # Escape email addresses to ensure safety
    escaped_emails = escape(email_addresses)
    
    # Split email addresses into a list
    email_list = escaped_emails.split(',')
    
    # Define a maximum number of addresses per mailto link
    MAX_EMAILS_PER_LINK = 50
    
    # Split the email addresses into smaller groups
    email_groups = [email_list[i:i + MAX_EMAILS_PER_LINK] for i in range(0, len(email_list), MAX_EMAILS_PER_LINK)]
    
    # Generate buttons for each batch of email links
    buttons_html = ""
    for i, group in enumerate(email_groups):
        mailto_link = f"mailto:?bcc={','.join(group)}?subject=Important Information&body=Please review the following information."
        buttons_html += f"""
        <button onclick="window.open('{mailto_link}', '_blank')">Open Batch {i + 1}</button><br>
        """
    
    # Generate the HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Send Emails</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
            }}
            button {{
                display: inline-block;
                padding: 10px 20px;
                font-size: 16px;
                color: #fff;
                background-color: #007bff;
                border: none;
                border-radius: 5px;
                text-decoration: none;
                cursor: pointer;
                margin: 5px;
            }}
            button:hover {{
                background-color: #0056b3;
            }}
        </style>
    </head>
    <body>
        <p>Click on the buttons below to open each batch of email addresses:</p>
        {buttons_html}
        <p><a href="javascript:history.back()" class="button">Go Back</a></p>
    </body>
    </html>
    """
    
    return HttpResponse(html_content, content_type='text/html')


