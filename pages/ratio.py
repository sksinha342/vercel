from flask import request, send_file
import io
from PIL import Image

def ratio_img():
    # 1. File check karein
    if 'image' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['image']
    target_kb = request.form.get('target_kb')
    
    if file.filename == '':
        return "No selected file", 400

    img = Image.open(file.stream)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img_io = io.BytesIO()
    
    if target_kb and target_kb.isdigit():
        target_bytes = int(target_kb) * 1024
        quality = 95
        
        # Initial save
        img.save(img_io, 'JPEG', quality=quality)
        
        # Quality adjust karein agar size bada hai
        while img_io.tell() > target_bytes and quality > 10:
            img_io.seek(0)
            img_io.truncate()
            quality -= 5
            img.save(img_io, 'JPEG', quality=quality)
    else:
        img.save(img_io, 'JPEG', quality=95)
    
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name="resized.jpg")