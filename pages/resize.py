from flask import Blueprint, request, send_file, render_template
import io
import math
from PIL import Image

# Blueprint name must match filename_bp logic in index.py
resize_bp = Blueprint("resize", __name__)

# Metadata for Dashboard
metadata = {
    "title": "Image Resizer & Compressor",
    "description": "Apni images ka size (KB) kam ya zyada karein aur quality maintain rakhein.",
    "image": "pages/imgcrop.jpg"
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

    # Open image
    img = Image.open(file.stream)
    original_format = img.format
    
    # Convert RGBA/P to RGB for JPEG
    if img.mode in ("RGBA", "P"):
        if img.mode == "RGBA":
            # Create white background for transparent images
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")
    
    # Apply smart compression
    img_io = smart_compress_image(img, target_kb)
    
    return send_file(
        img_io,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name="resized.jpg"
    )


def smart_compress_image(img, target_kb=None):
    """
    Smart compression that can both reduce AND increase size
    """
    if target_kb and target_kb.isdigit():
        target_bytes = int(target_kb) * 1024
    else:
        # No target, use default quality
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG', quality=85, optimize=True)
        img_io.seek(0)
        return img_io
    
    # Get original size
    test_io = io.BytesIO()
    img.save(test_io, 'JPEG', quality=85, optimize=True)
    original_size = test_io.tell()
    
    # Decide strategy based on current vs target
    if original_size > target_bytes:
        # Need to COMPRESS (reduce size)
        return compress_to_target(img, target_bytes)
    elif original_size < target_bytes * 0.8:
        # Need to EXPAND (increase size)
        return expand_to_target(img, target_bytes)
    else:
        # Already close to target, just optimize
        return optimize_existing(img, target_bytes)


def compress_to_target(img, target_bytes):
    """
    Aggressive compression to hit target size
    """
    # Strategy 1: Binary search for optimal quality
    best_io = None
    best_size = float('inf')
    low, high = 10, 95
    
    for _ in range(15):  # 15 iterations for accuracy
        mid = (low + high) // 2
        test_io = io.BytesIO()
        img.save(test_io, 'JPEG', quality=mid, optimize=True, subsampling=2)
        test_size = test_io.tell()
        
        if test_size <= target_bytes:
            best_io = test_io
            best_size = test_size
            low = mid + 1
        else:
            high = mid - 1
    
    # If within 5% of target, return
    if best_io and best_size <= target_bytes * 1.05:
        best_io.seek(0)
        return best_io
    
    # Strategy 2: Resize image if needed
    if best_io is None or best_size > target_bytes:
        # Calculate scale factor
        current_size = best_size if best_io else target_bytes * 2
        scale_factor = math.sqrt(target_bytes / current_size) * 0.85
        scale_factor = max(0.3, min(0.9, scale_factor))
        
        new_width = max(100, int(img.width * scale_factor))
        new_height = max(100, int(img.height * scale_factor))
        
        # Use high-quality resampling
        if scale_factor < 0.6:
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            resized = img.resize((new_width, new_height), Image.Resampling.BICUBIC)
        
        # Try with moderate quality
        test_io = io.BytesIO()
        resized.save(test_io, 'JPEG', quality=75, optimize=True, subsampling=2)
        
        if test_io.tell() <= target_bytes:
            test_io.seek(0)
            return test_io
        
        # Strategy 3: Try WebP format (better compression)
        webp_io = io.BytesIO()
        img.save(webp_io, 'WEBP', quality=70, method=6)
        if webp_io.tell() <= target_bytes:
            webp_io.seek(0)
            # Return as JPEG but with WebP compression (still compatible)
            return webp_io
    
    # Fallback: Return best available
    if best_io:
        best_io.seek(0)
        return best_io
    
    # Final fallback
    final_io = io.BytesIO()
    img.save(final_io, 'JPEG', quality=50, optimize=True)
    final_io.seek(0)
    return final_io


def expand_to_target(img, target_bytes):
    """
    Increase image size to meet target
    """
    # Strategy 1: Increase quality to maximum
    for quality in [92, 95, 98, 100]:
        test_io = io.BytesIO()
        img.save(test_io, 'JPEG', quality=quality, optimize=False, subsampling=0)
        if test_io.tell() >= target_bytes:
            test_io.seek(0)
            return test_io
    
    # Strategy 2: Disable optimization
    test_io = io.BytesIO()
    img.save(test_io, 'JPEG', quality=95, optimize=False, progressive=False)
    current_size = test_io.tell()
    
    if current_size < target_bytes:
        # Strategy 3: Slight upscaling
        scale_factor = min(1.3, math.sqrt(target_bytes / current_size))
        if scale_factor > 1.05:
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            
            # Use LANCZOS for upscaling (best quality)
            upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            final_io = io.BytesIO()
            upscaled.save(final_io, 'JPEG', quality=95, optimize=False)
            final_io.seek(0)
            return final_io
    
    test_io.seek(0)
    return test_io


def optimize_existing(img, target_bytes):
    """
    Fine-tune existing image to hit target precisely
    """
    # Try to get as close as possible to target
    best_io = None
    best_diff = float('inf')
    
    for quality in [95, 92, 90, 88, 85, 82, 80, 78, 75]:
        test_io = io.BytesIO()
        img.save(test_io, 'JPEG', quality=quality, optimize=True)
        size = test_io.tell()
        diff = abs(size - target_bytes)
        
        if diff < best_diff:
            best_diff = diff
            best_io = test_io
        
        if size <= target_bytes and target_bytes - size < target_bytes * 0.05:
            best_io.seek(0)
            return best_io
    
    if best_io:
        best_io.seek(0)
        return best_io
    
    # Fallback
    final_io = io.BytesIO()
    img.save(final_io, 'JPEG', quality=85, optimize=True)
    final_io.seek(0)
    return final_io


# Optional: Add batch processing endpoint
@resize_bp.route("/resize_batch", methods=["POST"])
def batch_resize():
    """
    Process multiple images with same target size
    """
    if 'images' not in request.files:
        return "No files uploaded", 400
    
    files = request.files.getlist('images')
    target_kb = request.form.get('target_kb')
    
    if not files:
        return "No files selected", 400
    
    import zipfile
    zip_io = io.BytesIO()
    
    with zipfile.ZipFile(zip_io, 'w') as zipf:
        for idx, file in enumerate(files):
            if file.filename:
                img = Image.open(file.stream)
                if img.mode in ("RGBA", "P"):
                    if img.mode == "RGBA":
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    else:
                        img = img.convert("RGB")
                
                img_io = smart_compress_image(img, target_kb)
                
                # Get original name without extension
                name = file.filename.rsplit('.', 1)[0]
                zipf.writestr(f"{name}_compressed.jpg", img_io.getvalue())
    
    zip_io.seek(0)
    return send_file(
        zip_io,
        mimetype='application/zip',
        as_attachment=True,
        download_name="compressed_images.zip"
    )


# Optional: Get image info without processing
@resize_bp.route("/image_info", methods=["POST"])
def get_image_info():
    """
    Get image information and estimated sizes
    """
    if 'image' not in request.files:
        return {"error": "No file"}, 400
    
    file = request.files['image']
    img = Image.open(file.stream)
    
    # Calculate estimated sizes at different qualities
    estimates = {}
    for quality in [60, 70, 80, 85, 90, 95]:
        test_io = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img_copy = img.convert("RGB")
            img_copy.save(test_io, 'JPEG', quality=quality, optimize=True)
        else:
            img.save(test_io, 'JPEG', quality=quality, optimize=True)
        estimates[f"{quality}%"] = round(test_io.tell() / 1024, 1)
    
    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "mode": img.mode,
        "file_size_kb": round(file.tell() / 1024, 1) if hasattr(file, 'tell') else None,
        "estimated_sizes_kb": estimates
    }