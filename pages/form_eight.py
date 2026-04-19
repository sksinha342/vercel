import os
import io
import uuid
import random
import pyvips
from flask import Blueprint, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# 1. Blueprint Setup
form_eight_bp = Blueprint('form_eight', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "form_viii_base.jpg")

def get_hindi_font(size=28):
    font_paths = [
        os.path.join(BASE_DIR, "fonts", "Kalam-Regular.ttf"),
        os.path.join(BASE_DIR, "Kalam-Regular.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: continue
    return ImageFont.load_default()

# --- NAYA FUNCTION: Sirf Income ke liye (Pyvips Rendering) ---
def render_vips_text(text, size=28, color="darkblue"):
    """Pyvips ka use karke joint characters ko sahi se render karta hai"""
    # Termux/Linux mein font family ka naam 'Kalam' hona chahiye (fc-list check karein)
    # Agar path se load karna hai toh 'Kalam @/path/to/font.ttf' format try karein
    vips_font = f"Kalam {size}"
    
    # Text image create karein (DPI badhane se quality badhegi)
    timg = pyvips.Image.text(text, font=vips_font, rgba=True, dpi=300)
    
    # Isko Pillow Image mein convert karein
    mem_vips = timg.write_to_memory()
    return Image.frombuffer('RGBA', (timg.width, timg.height), mem_vips, 'raw', 'RGBA', 0, 1)

def draw_vips_income(img, text, x, y, size, rotate=False):
    """Income field par rotation aur vips quality apply karne ke liye"""
    if not text: return
    
    # Vips se Hindi text image generate karein
    text_layer = render_vips_text(str(text), size=size)
    
    if rotate:
        max_rot = 2.5 if len(str(text)) > 15 else 1.2
        rotation_angle = random.uniform(-max_rot, max_rot)
        text_layer = text_layer.rotate(rotation_angle, expand=1, resample=Image.BICUBIC)
    
    # Paste on base image
    img.paste(text_layer, (x, y), text_layer)

def draw_handwriting(draw, text, x, y, font):
    """Normal fields ke liye purana character-by-character logic"""
    if not text: return y
    current_x, current_y = x, y
    for char in str(text):
        if char == ' ':
            current_x += 12
            continue
        char_x = current_x + random.randint(-1, 1)
        char_y = current_y + random.randint(-1, 1)
        draw.text((char_x, char_y), char, font=font, fill="darkblue")
        try:
            bbox = draw.textbbox((0, 0), char, font=font)
            current_x += (bbox[2] - bbox[0]) + 0.5
        except:
            current_x += 18
    return current_y + 38

@form_eight_bp.route('/form_eight')
def index():
    return render_template('form_eight.html')

@form_eight_bp.route('/form_eight/generate', methods=['POST'])
def generate():
    data = {
        'name': request.form.get('name', ''),
        'father': request.form.get('father_name', ''),
        'village': request.form.get('village', ''),
        'post_office': request.form.get('post_office', ''),
        'thana': request.form.get('thana', ''),
        'block': request.form.get('block', ''),
        'subdivision': request.form.get('subdivision', ''),
        'district': request.form.get('district', ''),
        'state': request.form.get('state', 'बिहार'),
        'caste': request.form.get('caste', ''),
        'annual_income': request.form.get('annual_income', ''),
        'total_income': request.form.get('total_income', ''),
        'date': request.form.get('date', datetime.now().strftime('%d/%m/%Y')),
        'signature': request.form.get('signature', ''),
    }
    
    if not os.path.exists(BASE_IMAGE_PATH):
        return "Base image not found!"

    img = Image.open(BASE_IMAGE_PATH).convert('RGBA')
    draw = ImageDraw.Draw(img)
    default_font = get_hindi_font(28)
    
    # 1. Normal Handwriting Fields (No change)
    fields = [
        (data['name'], 210, 245), (data['father'], 715, 236),
        (data['village'], 240, 285), (data['post_office'], 673, 275),
        (data['thana'], 960, 270), (data['block'], 150, 325),
        (data['subdivision'], 408, 328), (data['district'], 629, 325),
        (data['state'], 850, 320), (data['caste'], 233, 410)
    ]
    for text, x, y in fields:
        draw_handwriting(draw, text, x, y, default_font)
    
    # 2. Income Fields (Using Pyvips for High Quality Hindi)
    if data['annual_income']:
        draw_vips_income(img, data['annual_income'], 710, 835, size=28)
    
    if data['total_income']:
        val = str(data['total_income'])
        f_size = 26
        if len(val) > 18: f_size = 18
        elif len(val) > 12: f_size = 21
        # Baseline adjust: 915 ki jagah 905 use kiya hai rotation space ke liye
        draw_vips_income(img, val, 122, 905, size=f_size, rotate=True)
    
    # 3. Footer Fields
    draw_handwriting(draw, data['date'], 213, 1572, default_font)
    draw_handwriting(draw, data['village'], 213, 1532, default_font)
    sign_text = data['signature'] if data['signature'] else "______________"
    draw_handwriting(draw, sign_text, 800, 1525, default_font)
    
    # Save to memory and return
    img_io = io.BytesIO()
    final_img = img.convert('RGB')
    final_img.save(img_io, 'JPEG', quality=95) # Quality badha di gayi hai
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name="OBC_Form.jpg")
