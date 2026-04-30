from flask import Blueprint, request, send_file, render_template, jsonify
import io, json, cv2
import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import base64
metadata = {
    "title": "Document Scanner ",
    "description": "Apni images ka size (KB) kam ya zyada karein aur quality maintain rakhein.",
    "image": "pages/docscan.jpg"
}
doclike_bp = Blueprint("doclike", __name__)

@doclike_bp.route("/doclike", methods=["GET", "POST"])
def doclike_main():
    if request.method == "GET":
        return render_template("doclike.html")
    
    action = request.form.get('action', 'process_single')
    
    try:
        if action == 'process_single':
            return process_single_image(request)
        elif action == 'merge_pdf':
            return merge_pdfs(request)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return "Invalid action", 400

def process_single_image(request):
    file = request.files.get('image')
    if not file:
        return jsonify({"error": "No image uploaded"}), 400
    
    # Safely load points
    try:
        points = json.loads(request.form.get('points'))
    except:
        return jsonify({"error": "Invalid points data"}), 400

    rotate_angle = int(request.form.get('rotate', 0))
    target_kb = request.form.get('target_kb')
    
    # Core Processing
    _, img_io, _ = process_image_with_loop_compression(file, points, rotate_angle, target_kb)
    
    if request.form.get('as_pdf') == 'true':
        pdf_io = convert_to_pdf_with_loop_compression([img_io], target_kb)
        return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name='scanned.pdf')
    
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='scanned.jpg')

def process_image_with_loop_compression(file, points, rotate_angle, target_kb=None):
    # Read image from stream
    img_array = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    # 1. Perspective Transform (Warping)
    pts1 = np.float32(points)
    # Calculate target dimensions based on points
    w1 = np.linalg.norm(pts1[0]-pts1[1])
    w2 = np.linalg.norm(pts1[2]-pts1[3])
    h1 = np.linalg.norm(pts1[0]-pts1[3])
    h2 = np.linalg.norm(pts1[1]-pts1[2])
    
    max_w = int(max(w1, w2))
    max_h = int(max(h1, h2))
    
    pts2 = np.float32([[0,0], [max_w,0], [max_w,max_h], [0,max_h]])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    result = cv2.warpPerspective(img, matrix, (max_w, max_h))
    
    # 2. To PIL for Rotation & Compression
    pil_img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    if rotate_angle != 0:
        pil_img = pil_img.rotate(rotate_angle, expand=True)
    
    # 3. Compression Loop
    output_buffer, info = compress_with_loop(pil_img, target_kb)
    return pil_img, output_buffer, info

def compress_with_loop(pil_img, target_kb=None):
    target_bytes = int(target_kb) * 1024 if (target_kb and target_kb.isdigit()) else None
    img_io = io.BytesIO()
    
    if not target_bytes:
        pil_img.save(img_io, 'JPEG', quality=85, optimize=True)
        img_io.seek(0)
        return img_io, {"quality": 85}

    # Technique: Precise Binary Search
    low, high = 5, 95
    best_io = io.BytesIO()
    
    for _ in range(8): # 8 iterations is enough for 1-100 range
        mid = (low + high) // 2
        test_io = io.BytesIO()
        pil_img.save(test_io, 'JPEG', quality=mid, optimize=True)
        if test_io.tell() <= target_bytes:
            best_io = test_io
            low = mid + 1
        else:
            high = mid - 1
            
    # Fallback: Resize if still too large at min quality
    if best_io.tell() == 0 or best_io.tell() > target_bytes:
        scale = 0.8
        while scale > 0.2:
            w, h = int(pil_img.width * scale), int(pil_img.height * scale)
            resized = pil_img.resize((w, h), Image.Resampling.LANCZOS)
            test_io = io.BytesIO()
            resized.save(test_io, 'JPEG', quality=40, optimize=True)
            if test_io.tell() <= target_bytes:
                best_io = test_io
                break
            scale -= 0.2

    best_io.seek(0)
    return best_io, {}