from flask import Blueprint, request, send_file, render_template, session
import io, json, cv2
import numpy as np
from PIL import Image
import img2pdf
import math
import tempfile
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import base64

doclike_bp = Blueprint("doclike", __name__)

# Metadata for Dashboard
metadata = {
    "title": "Smart Doc Scanner",
    "description": "Multi-page document scanner with perspective correction and PDF merging.",
    "image": "pages/docscan.jpg" 
}

@doclike_bp.route("/doclike", methods=["GET", "POST"])
def doclike_main():
    if request.method == "GET":
        return render_template("doclike.html")
    
    action = request.form.get('action', 'process')
    
    if action == 'process_single':
        return process_single_image(request)
    elif action == 'process_batch':
        return process_batch_images(request)
    elif action == 'merge_pdf':
        return merge_pdfs(request)
    
    return "Invalid action", 400


def process_single_image(request):
    """Process a single image with perspective correction"""
    file = request.files.get('image')
    if not file:
        return json.jsonify({"error": "No image uploaded"}), 400
    
    points = json.loads(request.form.get('points'))
    rotate_angle = int(request.form.get('rotate', 0))
    target_kb = request.form.get('target_kb')
    quality_preset = request.form.get('quality', 'auto')
    
    # Process image
    result_img, img_io = process_image(file, points, rotate_angle, target_kb, quality_preset)
    
    if request.form.get('as_pdf') == 'true':
        pdf_io = convert_to_pdf_with_reportlab([img_io], target_kb)
        return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name='scanned_document.pdf')
    
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='scanned_document.jpg')


def process_batch_images(request):
    """Process multiple images and store in session"""
    files = request.files.getlist('images')
    if not files:
        return json.jsonify({"error": "No images uploaded"}), 400
    
    points_list = json.loads(request.form.get('points_list', '[]'))
    rotate_angle = int(request.form.get('rotate', 0))
    target_kb = request.form.get('target_kb')
    quality_preset = request.form.get('quality', 'auto')
    
    processed_images = []
    
    for idx, file in enumerate(files):
        points = points_list[idx] if idx < len(points_list) else None
        if not points:
            points = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
        
        result_img, img_io = process_image(file, points, rotate_angle, target_kb, quality_preset)
        
        # Store as base64 for session
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        processed_images.append({
            'data': img_base64,
            'size': img_io.tell()
        })
    
    # Store in session
    session['processed_images'] = processed_images
    
    return json.jsonify({
        "success": True,
        "count": len(processed_images),
        "images": [{"index": i, "size_kb": img['size']/1024} for i, img in enumerate(processed_images)]
    })


def process_image(file, points, rotate_angle, target_kb=None, quality_preset='auto'):
    """Core image processing function"""
    in_memory_file = io.BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    
    # Perspective Transform
    pts1 = np.float32([[p[0], p[1]] for p in points])
    width = int(max(np.linalg.norm(pts1[0]-pts1[1]), np.linalg.norm(pts1[2]-pts1[3])))
    height = int(max(np.linalg.norm(pts1[0]-pts1[3]), np.linalg.norm(pts1[1]-pts1[2])))
    pts2 = np.float32([[0,0], [width,0], [width,height], [0,height]])
    
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    result = cv2.warpPerspective(img, matrix, (width, height))
    
    # Convert to PIL
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(result_rgb)
    
    if rotate_angle != 0:
        pil_img = pil_img.rotate(rotate_angle, expand=True)
    
    # Apply advanced compression
    output_buffer = compress_image_advanced(pil_img, target_kb, quality_preset)
    
    return pil_img, output_buffer


def compress_image_advanced(pil_img, target_kb=None, quality_preset='auto'):
    """
    Advanced image compression with multiple strategies
    """
    img_io = io.BytesIO()
    
    # Default quality based on preset
    quality_map = {
        'low': 60,
        'medium': 75,
        'high': 90,
        'auto': 85
    }
    
    initial_quality = quality_map.get(quality_preset, 85)
    
    # Strategy 1: Save with quality adjustment
    pil_img.save(img_io, 'JPEG', quality=initial_quality, optimize=True, progressive=True)
    current_size = img_io.tell()
    
    if target_kb and target_kb.isdigit():
        target_bytes = int(target_kb) * 1024
        
        # If need to reduce size
        if current_size > target_bytes:
            img_io = compress_to_target(pil_img, target_bytes, initial_quality)
        
        # If need to increase size
        elif current_size < target_bytes and target_bytes > current_size * 1.2:
            img_io = expand_to_target(pil_img, target_bytes, initial_quality)
    
    img_io.seek(0)
    return img_io


def compress_to_target(pil_img, target_bytes, start_quality=85):
    """
    Aggressive compression to hit target size using multiple techniques
    """
    # Technique 1: Quality reduction with binary search
    low, high = 10, start_quality
    best_io = None
    best_size = float('inf')
    
    for _ in range(15):  # More iterations for better accuracy
        mid = (low + high) // 2
        test_io = io.BytesIO()
        
        pil_img.save(test_io, 'JPEG', quality=mid, optimize=True, subsampling=2)
        test_size = test_io.tell()
        
        if test_size <= target_bytes:
            best_io = test_io
            best_size = test_size
            low = mid + 1
        else:
            high = mid - 1
    
    if best_io and best_size <= target_bytes * 1.05:
        return best_io
    
    # Technique 2: Smart resizing
    if best_io is None or best_size > target_bytes:
        # Calculate optimal scale factor
        current_area = pil_img.width * pil_img.height
        target_area = current_area * (target_bytes / best_size) if best_size > 0 else current_area * 0.7
        scale_factor = math.sqrt(target_area / current_area)
        scale_factor = max(0.3, min(0.95, scale_factor))
        
        new_width = max(100, int(pil_img.width * scale_factor))
        new_height = max(100, int(pil_img.height * scale_factor))
        
        # Use LANCZOS for better quality when downscaling
        resized = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Try different quality levels
        for quality in [75, 65, 55, 45]:
            test_io = io.BytesIO()
            resized.save(test_io, 'JPEG', quality=quality, optimize=True, subsampling=2)
            if test_io.tell() <= target_bytes:
                return test_io
        
        # Technique 3: Convert to grayscale for extreme compression
        if test_io.tell() > target_bytes * 1.2:
            grayscale = resized.convert('L')
            for quality in [70, 60, 50]:
                gray_io = io.BytesIO()
                grayscale.save(gray_io, 'JPEG', quality=quality, optimize=True)
                if gray_io.tell() <= target_bytes:
                    return gray_io
    
    # Fallback: Return best available
    if best_io:
        return best_io
    
    # Final fallback - aggressive compression
    final_io = io.BytesIO()
    small_img = pil_img.resize((max(100, pil_img.width//2), max(100, pil_img.height//2)), Image.Resampling.LANCZOS)
    small_img.save(final_io, 'JPEG', quality=40, optimize=True)
    return final_io


def expand_to_target(pil_img, target_bytes, start_quality=85):
    """
    Increase image size to meet target (add metadata or reduce compression)
    """
    # Technique 1: Increase quality progressively
    for quality in [92, 95, 98, 100]:
        test_io = io.BytesIO()
        pil_img.save(test_io, 'JPEG', quality=quality, optimize=False)
        if test_io.tell() >= target_bytes:
            return test_io
    
    # Technique 2: Remove optimization
    test_io = io.BytesIO()
    pil_img.save(test_io, 'JPEG', quality=92, optimize=False, progressive=False)
    current_size = test_io.tell()
    
    if current_size < target_bytes:
        # Technique 3: Slight upscale
        scale_factor = min(1.5, math.sqrt(target_bytes / current_size))
        if scale_factor > 1.05:
            new_width = int(pil_img.width * scale_factor)
            new_height = int(pil_img.height * scale_factor)
            upscaled = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            final_io = io.BytesIO()
            upscaled.save(final_io, 'JPEG', quality=95, optimize=False)
            if final_io.tell() <= target_bytes * 1.2:
                return final_io
    
    return test_io


def convert_to_pdf_with_reportlab(image_buffers, target_kb=None):
    """
    Convert multiple images to a single PDF with proper margins and white background
    """
    pdf_io = io.BytesIO()
    
    # Calculate per-image target if overall target specified
    per_image_target = None
    if target_kb and target_kb.isdigit():
        total_target = int(target_kb) * 1024
        per_image_target = total_target // len(image_buffers) if image_buffers else total_target
    
    # Create PDF with white background
    c = canvas.Canvas(pdf_io, pagesize=A4)
    page_width, page_height = A4
    
    # Margins (1 inch margins = 72 points)
    margin = 72
    content_width = page_width - (2 * margin)
    content_height = page_height - (2 * margin)
    
    for idx, img_buffer in enumerate(image_buffers):
        img_buffer.seek(0)
        
        # Re-compress image if per-image target specified
        if per_image_target:
            pil_img = Image.open(img_buffer)
            compressed_buffer = compress_to_target(pil_img, per_image_target, 85)
            compressed_buffer.seek(0)
            img_buffer = compressed_buffer
        
        # Open image
        img_buffer.seek(0)
        pil_img = Image.open(img_buffer)
        
        # Calculate dimensions to fit page with margins
        img_width, img_height = pil_img.size
        width_ratio = content_width / img_width
        height_ratio = content_height / img_height
        scale = min(width_ratio, height_ratio)
        
        draw_width = img_width * scale
        draw_height = img_height * scale
        
        # Center on page
        x = (page_width - draw_width) / 2
        y = (page_height - draw_height) / 2
        
        # Create ImageReader and draw
        img_reader = ImageReader(pil_img)
        c.drawImage(img_reader, x, y, width=draw_width, height=draw_height)
        
        # Add page number (except on last page if not needed)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(page_width - 50, margin - 15, f"Page {idx + 1}")
        
        # Add new page for next image (except after last)
        if idx < len(image_buffers) - 1:
            c.showPage()
    
    c.save()
    pdf_io.seek(0)
    
    # Final compression if needed
    if target_kb and target_kb.isdigit():
        pdf_io = compress_pdf(pdf_io, int(target_kb) * 1024)
    
    return pdf_io


def compress_pdf(pdf_io, target_bytes):
    """
    Compress PDF by adjusting image qualities
    """
    pdf_io.seek(0)
    current_size = pdf_io.tell()
    
    if current_size <= target_bytes:
        return pdf_io
    
    # If PDF is too large, we need to recompress all images
    # This is a placeholder - in production, you'd use PyPDF2 or similar
    # For now, return as is with a warning
    pdf_io.seek(0)
    return pdf_io


def merge_pdfs(request):
    """Merge multiple processed PDFs"""
    data = request.get_json()
    images_data = data.get('images', [])
    
    if not images_data:
        return json.jsonify({"error": "No images to merge"}), 400
    
    pdf_buffer = convert_to_pdf_with_reportlab(images_data, data.get('target_kb'))
    
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name='merged_document.pdf')