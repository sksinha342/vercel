import os
import io
import uuid
import random
from flask import Blueprint, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import requests  # नया import - Vercel पर font download करने के लिए

# 1. Blueprint Setup
form_eight_bp = Blueprint('form_eight', __name__)

metadata = {
    "title": "OBC Form VIII Generator",
    "description": "Handwriting style Hindi form filler for OBC certificates.",
    "image": "pages/form8.jpg"
}

# --- पाथ सेटिंग: जो Vercel और Local दोनों जगह काम करे ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "form_viii_base.jpg")

def get_hindi_font(size=28):
    """Vercel और Local दोनों पर Hindi font सही से रेंडर करेगा"""
    
    # पहले Local fonts check करें
    local_font_paths = [
        os.path.join(BASE_DIR, "fonts", "Kalam-Regular.ttf"),
        os.path.join(BASE_DIR, "fonts", "Mukta-Regular.ttf"),
        os.path.join(BASE_DIR, "Kalam-Regular.ttf"),
        os.path.join(BASE_DIR, "NotoSansDevanagari-Regular.ttf"),
    ]
    
    for path in local_font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # Vercel के Linux system fonts check करें
    system_fonts = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    for path in system_fonts:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # ⭐ Vercel के लिए मुख्य Fix: Google Fonts से बाइनरी डेटा लोड करें
    # यह तरीका हर बार काम करेगा क्योंकि Vercel पर बाहरी requests allowed हैं
    try:
        import tempfile
        # Noto Sans Devanagari (Google Fonts)
        font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
        
        # Font को temporary file में save करें
        temp_font = tempfile.NamedTemporaryFile(delete=False, suffix='.ttf')
        response = requests.get(font_url, timeout=10)
        if response.status_code == 200:
            temp_font.write(response.content)
            temp_font.close()
            font_obj = ImageFont.truetype(temp_font.name, size)
            # Cleanup later (optional)
            return font_obj
    except Exception as e:
        print(f"Font download failed: {e}")
    
    # Last resort: Default font
    return ImageFont.load_default()

def draw_clean_text(draw, img, text, x, y, font, rotate=False):
    """सिर्फ वर्ड स्पेसिंग और रोटेशन के साथ टेक्स्ट ड्रा करना"""
    if not text: return
    text_str = str(text)
    
    if rotate:
        max_rot = 2.5 if len(text_str) > 15 else 1.2
        rotation_angle = random.uniform(-max_rot, max_rot)
        text_layer = Image.new('RGBA', (700, 120), (255, 255, 255, 0))
        text_draw = ImageDraw.Draw(text_layer)
        
        words = text_str.split(' ')
        curr_x = 10
        word_gap = 15
        
        for word in words:
            text_draw.text((curr_x, 20), word, font=font, fill="darkblue")
            bbox = text_draw.textbbox((curr_x, 20), word, font=font)
            curr_x += (bbox[2] - bbox[0]) + word_gap
            
        rotated_text = text_layer.rotate(rotation_angle, expand=1, resample=Image.BICUBIC)
        img.paste(rotated_text, (x, 925 - 25), rotated_text) 
    else:
        draw.text((x, y), text_str, font=font, fill="darkblue")

def draw_handwriting(draw, text, x, y, font):
    """एक-एक अक्षर को हल्का रैंडम मूव करके हैंडराइटिंग लुक देना"""
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
        return f"Error: {BASE_IMAGE_PATH} not found. Path check karo bhai!"

    img = Image.open(BASE_IMAGE_PATH).convert('RGBA')
    draw = ImageDraw.Draw(img)
    default_font = get_hindi_font(28)
    
    # फॉर्म भरने का काम
    fields = [
        (data['name'], 210, 245), (data['father'], 715, 236),
        (data['village'], 240, 285), (data['post_office'], 673, 275),
        (data['thana'], 960, 270), (data['block'], 150, 325),
        (data['subdivision'], 408, 328), (data['district'], 629, 325),
        (data['state'], 850, 320), (data['caste'], 233, 410)
    ]
    for text, x, y in fields:
        draw_handwriting(draw, text, x, y, default_font)
    
    # ⚠️ यहाँ कुछ भी नहीं बदला - annual income वैसा ही है
    if data['annual_income']:
        draw_clean_text(draw, img, data['annual_income'], 710, 835, default_font)
    
    # ⚠️ यहाँ कुछ भी नहीं बदला - total income का font size/rotate logic वैसा ही है
    if data['total_income']:
        val = str(data['total_income'])
        f_size = 26
        if len(val) > 18: f_size = 18
        elif len(val) > 12: f_size = 21
        income_font = get_hindi_font(f_size)
        draw_clean_text(draw, img, val, 122, 915, income_font, rotate=True)
    
    draw_handwriting(draw, data['date'], 213, 1572, default_font)
    draw_handwriting(draw, data['village'], 213, 1532, default_font)
    sign_text = data['signature'] if data['signature'] else "______________"
    draw_handwriting(draw, sign_text, 800, 1525, default_font)
    
    # मेमोरी में सेव करें
    img_io = io.BytesIO()
    final_img = img.convert('RGB')
    final_img.save(img_io, 'JPEG', quality=40)
    img_io.seek(0)
    
    return send_file(
        img_io, 
        mimetype='image/jpeg', 
        as_attachment=True, 
        download_name="OBC_Form_VIII_Filled.jpg"
    )