from flask import Blueprint, request, send_file, render_template
import io, json, cv2
import numpy as np
from PIL import Image
import img2pdf
import math

doclike_bp = Blueprint("doclike", __name__)

# Metadata for Dashboard
metadata = {
    "title": "Smart Doc Scanner",
    "description": "Perspective crop karein aur image ko PDF ya Clean JPG mein badlein.",
    "image": "pages/docscan.jpg" 
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
    quality_preset = request.form.get('quality', 'auto')  # auto, low, medium, high

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
    
    # Convert to PIL for better compression
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(result_rgb)

    if rotate_angle != 0:
        pil_img = pil_img.rotate(rotate_angle, expand=True)

    # Apply advanced compression
    output_buffer = compress_image_advanced(pil_img, target_kb, quality_preset)
    
    if as_pdf:
        # PDF conversion with size optimization
        pdf_io = compress_to_pdf(output_buffer, target_kb)
        return send_file(pdf_io, mimetype='application/pdf', as_attachment=True, download_name='scanned_document.pdf')
    
    return send_file(output_buffer, mimetype='image/jpeg', as_attachment=True, download_name='scanned_document.jpg')


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
        
        # Strategy 2: If need to reduce size
        if current_size > target_bytes:
            img_io = compress_to_target(pil_img, target_bytes, initial_quality)
        
        # Strategy 3: If need to increase size (add metadata or less compression)
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
    
    for _ in range(12):  # More iterations for better accuracy
        mid = (low + high) // 2
        test_io = io.BytesIO()
        
        # Try JPEG first
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
    
    # Technique 2: Resize image (maintain aspect ratio)
    if best_io is None or best_size > target_bytes:
        scale_factor = math.sqrt(target_bytes / best_size) if best_size > 0 else 0.7
        scale_factor = max(0.3, min(0.9, scale_factor))
        
        new_width = int(pil_img.width * scale_factor)
        new_height = int(pil_img.height * scale_factor)
        
        # Use different resize filters based on scale
        if scale_factor < 0.5:
            resized = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            resized = pil_img.resize((new_width, new_height), Image.Resampling.BICUBIC)
        
        test_io = io.BytesIO()
        resized.save(test_io, 'JPEG', quality=75, optimize=True, subsampling=2)
        
        if test_io.tell() <= target_bytes:
            return test_io
        
        # Technique 3: Convert to grayscale for extreme compression
        if test_io.tell() > target_bytes * 1.2:
            grayscale = resized.convert('L')
            gray_io = io.BytesIO()
            grayscale.save(gray_io, 'JPEG', quality=65, optimize=True)
            if gray_io.tell() <= target_bytes:
                return gray_io
    
    # Fallback: Return best available
    if best_io:
        return best_io
    
    # Final fallback
    final_io = io.BytesIO()
    pil_img.save(final_io, 'JPEG', quality=50, optimize=True)
    return final_io


def expand_to_target(pil_img, target_bytes, start_quality=85):
    """
    Increase image size to meet target (add metadata or reduce compression)
    """
    # Technique 1: Increase quality
    for quality in [95, 98, 100]:
        test_io = io.BytesIO()
        pil_img.save(test_io, 'JPEG', quality=quality, optimize=False)
        if test_io.tell() >= target_bytes:
            return test_io
    
    # Technique 2: Remove optimization and add metadata
    test_io = io.BytesIO()
    pil_img.save(test_io, 'JPEG', quality=92, optimize=False, progressive=False)
    current_size = test_io.tell()
    
    if current_size < target_bytes:
        # Technique 3: Slight upscale if needed
        scale_factor = min(1.3, math.sqrt(target_bytes / current_size))
        if scale_factor > 1.05:
            new_width = int(pil_img.width * scale_factor)
            new_height = int(pil_img.height * scale_factor)
            upscaled = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            final_io = io.BytesIO()
            upscaled.save(final_io, 'JPEG', quality=95, optimize=False)
            return final_io
    
    return test_io


def compress_to_pdf(image_buffer, target_kb=None):
    """
    Generate PDF with size optimization
    """
    import tempfile
    import subprocess
    
    pdf_io = io.BytesIO()
    
    # Method 1: Use img2pdf (best quality/size ratio)
    try:
        pdf_bytes = img2pdf.convert(image_buffer.getvalue())
        pdf_io.write(pdf_bytes)
        pdf_size = pdf_io.tell()
        
        # If PDF needs size adjustment
        if target_kb and target_kb.isdigit():
            target_bytes = int(target_kb) * 1024
            
            if pdf_size > target_bytes:
                # Need smaller PDF - recompress image first
                image_buffer.seek(0)
                pil_img = Image.open(image_buffer)
                
                # Calculate new image quality
                ratio = target_bytes / pdf_size
                new_quality = max(30, min(85, int(85 * ratio)))
                
                # Recompress image
                temp_img_io = io.BytesIO()
                pil_img.save(temp_img_io, 'JPEG', quality=new_quality, optimize=True)
                temp_img_io.seek(0)
                
                # Regenerate PDF
                pdf_io = io.BytesIO()
                new_pdf_bytes = img2pdf.convert(temp_img_io.getvalue())
                pdf_io.write(new_pdf_bytes)
            
            elif pdf_size < target_bytes and target_bytes > pdf_size * 1.2:
                # Add metadata to increase size slightly
                pdf_io.seek(0)
                # Note: PDF metadata addition is complex, so we'll accept current size
    
    except Exception as e:
        # Fallback: Use PIL to PDF (slower but works)
        pdf_io = fallback_pdf_generation(image_buffer)
    
    pdf_io.seek(0)
    return pdf_io


def fallback_pdf_generation(image_buffer):
    """
    Fallback PDF generation using reportlab or simple method
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    pdf_io = io.BytesIO()
    c = canvas.Canvas(pdf_io, pagesize=letter)
    
    image_buffer.seek(0)
    pil_img = Image.open(image_buffer)
    
    # Calculate image size to fit page
    page_width, page_height = letter
    img_width, img_height = pil_img.size
    
    # Scale to fit page
    scale = min(page_width / img_width, page_height / img_height) * 0.9
    draw_width = img_width * scale
    draw_height = img_height * scale
    
    # Center on page
    x = (page_width - draw_width) / 2
    y = (page_height - draw_height) / 2
    
    # Save temp image
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        pil_img.save(tmp, 'JPEG', quality=85)
        tmp_path = tmp.name
    
    c.drawImage(tmp_path, x, y, width=draw_width, height=draw_height)
    c.save()
    
    # Cleanup
    import os
    os.unlink(tmp_path)
    
    pdf_io.seek(0)
    return pdf_io


# Optional: Add WebP support for better compression
@doclike_bp.route("/doclike_webp", methods=["POST"])
def doclike_webp():
    """
    Alternative endpoint with WebP support (better compression than JPEG)
    """
    file = request.files.get('image')
    if not file:
        return "No image uploaded", 400
    
    points = json.loads(request.form.get('points'))
    rotate_angle = int(request.form.get('rotate', 0))
    target_kb = request.form.get('target_kb')
    
    # Process image (same as above)
    in_memory_file = io.BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    
    # Perspective transform
    pts1 = np.float32([[p['x'], p['y']] for p in points])
    width = int(max(np.linalg.norm(pts1[0]-pts1[1]), np.linalg.norm(pts1[2]-pts1[3])))
    height = int(max(np.linalg.norm(pts1[0]-pts1[3]), np.linalg.norm(pts1[1]-pts1[2])))
    pts2 = np.float32([[0,0], [width,0], [width,height], [0,height]])
    
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    result = cv2.warpPerspective(img, matrix, (width, height))
    
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(result_rgb)
    
    if rotate_angle != 0:
        pil_img = pil_img.rotate(rotate_angle, expand=True)
    
    # Use WebP for better compression
    img_io = io.BytesIO()
    
    if target_kb and target_kb.isdigit():
        target_bytes = int(target_kb) * 1024
        
        # Binary search for WebP quality
        low, high = 10, 100
        best_io = None
        
        for _ in range(10):
            mid = (low + high) // 2
            test_io = io.BytesIO()
            pil_img.save(test_io, 'WEBP', quality=mid, method=6)
            size = test_io.tell()
            
            if size <= target_bytes:
                best_io = test_io
                low = mid + 1
            else:
                high = mid - 1
        
        if best_io:
            img_io = best_io
        else:
            pil_img.save(img_io, 'WEBP', quality=70, method=6)
    else:
        pil_img.save(img_io, 'WEBP', quality=85, method=6)
    
    img_io.seek(0)
    return send_file(img_io, mimetype='image/webp', as_attachment=True, download_name='scanned_document.webp')