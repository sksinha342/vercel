from flask import Blueprint, request, send_file, render_template
import io
from PIL import Image

# Blueprint name must match filename_bp logic in index.py
resize_bp = Blueprint("resize", __name__)

# Metadata for Dashboard
metadata = {
    "title": "Image Resizer & Compressor",
    "description": "Apni images ka size (KB) kam karein aur quality maintain rakhein.",
    "image": "logo.png"  # Sirf file ka naam likhein, path index.py sambhal lega
}

@resize_bp.route("/resize", methods=["GET", "POST"])
def ratio_img():
    if request.method == "GET":
        return render_template("ratio.html")

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
    quality = 95

    # Logic to hit target KB
    if target_kb and target_kb.isdigit():
        target_bytes = int(target_kb) * 1024
        img.save(img_io, 'JPEG', quality=quality)
        while img_io.tell() > target_bytes and quality > 10:
            img_io.seek(0)
            img_io.truncate()
            quality -= 5
            img.save(img_io, 'JPEG', quality=quality)
    else:
        img.save(img_io, 'JPEG', quality=95)

    img_io.seek(0)
    return send_file(
        img_io,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name="resized.jpg"
    )