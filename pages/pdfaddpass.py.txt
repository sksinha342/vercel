from PyPDF2 import PdfReader, PdfWriter
from flask import send_file, request
import io

def protect_pdf():
    # 1. Form se file aur password uthao
    file = request.files.get('pdf_file')
    password = request.form.get('password')

    if not file or not password:
        return "File ya password missing hai!", 400

    # 2. PDF ko read aur write karne ka setup
    reader = PdfReader(file)
    writer = PdfWriter()

    # Saare pages copy karo
    for page in reader.pages:
        writer.add_page(page)

    # 3. Password lagao
    writer.encrypt(password)

    # 4. Result ko memory mein save karo
    output_pdf = io.BytesIO()
    writer.write(output_pdf)
    output_pdf.seek(0)

    # 5. User ko file download ke liye bhej do
    return send_file(
        output_pdf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='protected_document.pdf'
    )
