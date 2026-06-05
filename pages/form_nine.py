import os
import io
import uuid
import random
from flask import Blueprint, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# 1. Blueprint Setup
form_nine_bp = Blueprint('form_nine', __name__)

metadata = {
    "title": "NCL ( Bihar ) Decleration Genretor",
    "description": "Handwriting style Hindi form filler for OBC certificates.",
    "image": "pages/form9.jpg"
}

# --- पाथ सेटिंग: जो Vercel और Local दोनों जगह काम करे ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "static", "OBC_Form_IX.jpg")

def get_hindi_font(size=54):
    """फोंट्स के लिए भी Absolute Path"""
    font_paths = [
        os.path.join(BASE_DIR, "fonts", "Kalam-Regular.ttf"),
        os.path.join(BASE_DIR, "fonts", "Mukta-Regular.ttf"),
        os.path.join(BASE_DIR, "Kalam-Regular.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", # Vercel Linux
    ]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: continue
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
        
        # --- सुधार: यहाँ 925 की जगह डायनामिक 'y' का इस्तेमाल किया है ---
        img.paste(rotated_text, (x, y - 25), rotated_text) 
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

@form_nine_bp.route('/form_nine')
def index():
    return render_template('form_nine.html')

@form_nine_bp.route('/form_nine/generate', methods=['POST'])
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
    default_font = get_hindi_font(54)
    
    # फॉर्म भरने का काम
    fields = [
        (data['name'], 455, 595), (data['father'], 1415, 558),
        (data['village'], 497, 675), (data['post_office'], 1318, 630),
        (data['thana'], 1770, 629), (data['block'], 370, 755),
        (data['subdivision'], 807, 742), (data['district'], 1325, 729),
        (data['state'], 1650, 717), (data['caste'], 497, 910)
    ]
    for text, x, y in fields:
        draw_handwriting(draw, text, x, y, default_font)
    
    if data['annual_income']:
        draw_clean_text(draw, img, data['annual_income'], 1415, 1665, default_font)
    
    if data['total_income']:
        val = str(data['total_income'])
        f_size = 54
        if len(val) > 18: f_size = 40
        elif len(val) > 12: f_size = 43
        income_font = get_hindi_font(f_size)
        
        # अब यह 1915 पोजीशन को सही से पकड़ेगा
        draw_clean_text(draw, img, val, 252, 1880, income_font, rotate=True)
    
    draw_handwriting(draw, data['date'], 486, 3142, default_font)
    draw_handwriting(draw, data['village'], 486, 3048, default_font)
    sign_text = data['signature'] if data['signature'] else "______________"
    draw_handwriting(draw, sign_text, 1600, 3025, default_font)
    
    # --- मेमोरी (RAM) में राइट करना ---
    img_io = io.BytesIO()
    final_img = img.convert('RGB')
    final_img.save(img_io, 'JPEG', quality=4)
    img_io.seek(0)
    
    return send_file(
        img_io, 
        mimetype='image/jpeg', 
        as_attachment=True, 
        download_name="OBC_Form_IX_Filled.jpg"
    )