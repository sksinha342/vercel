import os
import io
import uuid
import random
from flask import Blueprint, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# 1. Blueprint Setup
form_eight_bp = Blueprint('form_eight', __name__)

metadata = {
    "title": "OBC Form VIII Generator",
    "description": "Handwriting style Hindi form filler for OBC certificates.",
    "image": "pages/form8.jpg"
}

# --- पाथ सेटिंग ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "form_viii_base.jpg")

def get_hindi_font(size=28, force_mukta=False):
    """अगर force_mukta True है, तो सिर्फ Mukta फोंट ही ढूंढेगा"""
    font_name = "Mukta-Regular.ttf" if force_mukta else "Kalam-Regular.ttf"
    
    paths = [
        os.path.join(BASE_DIR, "fonts", font_name),
        os.path.join(BASE_DIR, font_name),
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_handwriting(draw, text, x, y, font, use_word_logic=False):
    """
    हैंडराइटिंग स्टाइल फंक्शन: 
    - use_word_logic=False (Default): एक-एक अक्षर लिखेगा (नाम, पता आदि के लिए)
    - use_word_logic=True: पूरे शब्द एक साथ लिखेगा (Income/शून्य के लिए)
    """
    if not text: return y
    current_x, current_y = x, y
    text_str = str(text)

    if use_word_logic:
        # --- Income के लिए Word-by-Word लॉजिक (ताकि संयुक्ताक्षर न टूटें) ---
        words = text_str.split(' ')
        for word in words:
            off_x = random.randint(-2, 2)
            off_y = random.randint(-1, 1)
            draw.text((current_x + off_x, current_y + off_y), word, font=font, fill="darkblue")
            bbox = draw.textbbox((0, 0), word, font=font)
            current_x += (bbox[2] - bbox[0]) + 15 
    else:
        # --- बाकी सब के लिए अक्षर-दर-अक्षर लॉजिक (असली हैंडराइटिंग फील) ---
        for char in text_str:
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

def draw_rotated_income(draw, img, text, x, y, font):
    """Total Income के लिए रोटेशन + Word लॉजिक"""
    if not text: return
    text_str = str(text)
    
    max_rot = 2.5 if len(text_str) > 15 else 1.2
    rotation_angle = random.uniform(-max_rot, max_rot)
    
    text_layer = Image.new('RGBA', (700, 120), (255, 255, 255, 0))
    text_draw = ImageDraw.Draw(text_layer)
    
    # यहाँ भी शब्द वाला लॉजिक ताकि 'शून्य' न टूटे
    words = text_str.split(' ')
    curr_x = 10
    for word in words:
        text_draw.text((curr_x, 20), word, font=font, fill="darkblue")
        bbox = text_draw.textbbox((curr_x, 20), word, font=font)
        curr_x += (bbox[2] - bbox[0]) + 15
        
    rotated_text = text_layer.rotate(rotation_angle, expand=1, resample=Image.BICUBIC)
    img.paste(rotated_text, (x, 925 - 25), rotated_text)

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
        return f"Error: {BASE_IMAGE_PATH} not found!"

    img = Image.open(BASE_IMAGE_PATH).convert('RGBA')
    draw = ImageDraw.Draw(img)
    default_font = get_hindi_font(28)
    
    # 1. साधारण फील्ड्स (अक्षर-दर-अक्षर लॉजिक)
    fields = [
        (data['name'], 210, 245), (data['father'], 715, 236),
        (data['village'], 240, 285), (data['post_office'], 673, 275),
        (data['thana'], 960, 270), (data['block'], 150, 325),
        (data['subdivision'], 408, 328), (data['district'], 629, 325),
        (data['state'], 850, 320), (data['caste'], 233, 410)
    ]
    for text, x, y in fields:
        draw_handwriting(draw, text, x, y, default_font, use_word_logic=False)
    
    # --- generate() के अंदर income वाले हिस्से में बदलाव ---

    # 2. Annual Income (Mukta font इस्तेमाल करें ताकि 'शून्य' न टूटे)
    if data['annual_income']:
        # यहाँ 'force_mukta=True' किया है
        income_font_static = get_hindi_font(28, force_mukta=True)
        draw_handwriting(draw, data['annual_income'], 710, 835, income_font_static, use_word_logic=True)
    
    # 3. Total Income (Mukta font + Rotation)
    if data['total_income']:
        val = str(data['total_income'])
        f_size = 26
        if len(val) > 12: f_size = 21
        # यहाँ भी 'force_mukta=True'
        income_font_rot = get_hindi_font(f_size, force_mukta=True)
        draw_rotated_income(draw, img, val, 122, 915, income_font_rot)

    # 4. बाकी नीचे के फील्ड्स
    draw_handwriting(draw, data['date'], 213, 1572, default_font, use_word_logic=False)
    draw_handwriting(draw, data['village'], 213, 1532, default_font, use_word_logic=False)
    sign_text = data['signature'] if data['signature'] else "______________"
    draw_handwriting(draw, sign_text, 800, 1525, default_font, use_word_logic=False)
    
    # Vercel Memory Save
    img_io = io.BytesIO()
    final_img = img.convert('RGB')
    final_img.save(img_io, 'JPEG', quality=40)
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name="OBC_Form_VIII_Filled.jpg")