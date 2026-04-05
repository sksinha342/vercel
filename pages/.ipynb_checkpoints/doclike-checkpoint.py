from flask import Blueprint, request, send_file, render_template
import io, json, cv2
import numpy as np
from PIL import Image
import img2pdf

doclike_bp = Blueprint("doclike", __name__)

# Metadata for Dashboard
metadata = {
    "title": "Smart Doc Scanner",
    "description": "Perspective crop karein aur image ko PDF ya Clean JPG mein badlein.",
    "image": "logo.png" 
}

@doclike_bp.route("/doclike", methods=["GET", "POST"])
def doclike_main():
    if request.method == "GET":
        return render_template("doclike.html")

    file = request.files.get('image')
    if not file:
        return "No image uploaded", 400

    points = json.loads(request.form.get('points'))
    rotate_angle = int(request.form.get('rotate', 0))
    target_kb = request.form.get('target_kb')
    as_pdf = request.form.get('as_pdf') == 'true'

    # Process image with OpenCV
    in_memory_file = io.BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)

    # Perspective Transform
    pts1 = np.float32([[p['x'], p['y']] for p in points])
    width = int(max(np.linalg.norm(pts1[0]-pts1[1]), np.linalg.norm(pts1[2]-pts1[3])))
    height = int(max(np.linalg.norm(pts1[0]-pts1[3]), np.linalg.norm(pts1[1]-pts1[2])))
    pts2 = np.float32([[0,0], [width,0], [width,height], [0,height]])
    
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    result = cv2.warpPerspective(img, matrix, (width, height))
    
    # PIL for compression
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(result_rgb)

    if rotate_angle != 0:
        pil_img = pil_img.rotate(rotate_angle, expand=True)

    img_io = io.BytesIO()
    quality = 95
    pil_img.save(img_io, 'JPEG', quality=quality)
    
    # Compress to KB
    if target_kb and target_kb.isdigit():
        target_bytes = int(target_kb) * 1024
        while img_io.tell() > target_bytes and quality > 10:
            img_io.seek(0)
            img_io.truncate()
            quality -= 5
            pil_img.save(img_io, 'JPEG', quality=quality)

    img_io.seek(0)

    if as_pdf:
        pdf_io = io.BytesIO()
        pdf_bytes = img2pdf.convert(img_io.getvalue())
        pdf_io.write(pdf_bytes)
        pdf_io.seek(0)
        return send_file(pdf_io, mimetype='application/pdf')
    
    return send_file(img_io, mimetype='image/jpeg')