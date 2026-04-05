import qrcode
import io
import base64
from flask import render_template, request

def generate_qr(text):
    if not text:
        return render_template('qrgen.html', error="Kuch text toh likho!")

    # 1. QR Code banayein
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # 2. Image ko memory mein save karein
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    # 3. Base64 string mein convert karein (HTML mein dikhane ke liye)
    img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
    qr_data_url = f"data:image/png;base64,{img_base64}"

    # Wapas template par bhej dein image link ke saath
    return render_template('qrgen.html', qr_image=qr_data_url, old_data=text)
