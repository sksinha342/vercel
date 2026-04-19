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

def get_hindi_font(size=28):
    font_paths = [
        os.path.join(BASE_DIR, "fonts", "Kalam-Regular.ttf"),
        os.path.join(BASE_DIR, "fonts", "Mukta-Regular.ttf"),
        os.path.join(BASE_DIR, "Kalam-Regular.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf", 
    ]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: continue
    return ImageFont.load_default()

def draw_clean_text(draw, img, text, x, y, font, rotate=False):
    if not text: return
    text_str = str(text)
    
    if rotate:
        max_rot = 2.5 if len(text_str) > 15 else 1.2
        rotation_angle = random.uniform(-max_rot, max_rot)
        text_layer = Image.new('RGBA', (700, 120), (255, 255, 255, 0))
        text_draw = ImageDraw.Draw(text_layer)
        
        # रोटेशन में भी शब्दों को एक साथ ड्रा करें
        words = text_str.split(' ')
        curr_x = 10
        for word in words:
            text_draw.text((curr_x, 20), word, font=font, fill="darkblue")
            bbox = text_draw.textbbox((curr_x, 20), word, font=font)
            curr_x += (bbox[2] - bbox[0]) + 15
            
        rotated_text = text_layer.rotate(rotation_angle, expand=1, resample=Image.BICUBIC)
        img.paste(rotated_text, (x, 925 - 25), rotated_text) 
    else:
        # सीधा लिखने के लिए भी पूरा टेक्स्ट एक बार में दें ताकि संयुक्ताक्षर न टूटें
        draw.text((x, y), text_str, font=font, fill="darkblue")

def draw_handwriting(draw, text, x, y, font):
    """
    FIX: यहाँ अब हम एक-एक अक्षर नहीं, बल्कि पूरे शब्दों को ड्रा करेंगे।
    इससे 'शून्य' जैसे शब्द Vercel पर नहीं टूटेंगे।
    """
    if not text: return y
    current_x, current_y = x, y
    
    # शब्दों में तोड़ें ताकि 'न्' + 'य' साथ में रेंडर हों
    words = str(text).split(' ')
    
    for word in words:
        # हल्का सा नेचुरल रैंडम मूवमेंट सिर्फ शब्द के लिए
        off_x = random.randint(-1, 1)
        off_y = random.randint(-1, 1)
        
        # पूरे शब्द को एक साथ लिखें
        draw.text((current_x + off_x, current_y + off_y), word, font=font, fill="darkblue")
        
        # अगले शब्द के लिए जगह नापें
        try:
            bbox = draw.textbbox((0, 0), word, font=font)
            current_x += (bbox[2] - bbox[0]) + 15 # शब्दों के बीच का स्पेस
        except:
            current_x += (len(word) * 18) + 15
            
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
        return f"Error: {BASE_IMAGE_PATH} not found!"

    img = Image.open(BASE_IMAGE_PATH).convert('RGBA')
    draw = ImageDraw.Draw(img)
    default_font = get_hindi_font(28)
    
    fields = [
        (data['name'], 210, 245), (data['father'], 715, 236),
        (data['village'], 240, 285), (data['post_office'], 673, 275),
        (data['thana'], 960, 270), (data['block'], 150, 325),
        (data['subdivision'], 408, 328), (data['district'], 629, 325),
        (data['state'], 850, 320), (data['caste'], 233, 410)
    ]
    for text, x, y in fields:
        draw_handwriting(draw, text, x, y, default_font)
    
    if data['annual_income']:
        draw_clean_text(draw, img, data['annual_income'], 710, 835, default_font)
    
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
    
    img_io = io.BytesIO()
    final_img = img.convert('RGB')
    final_img.save(img_io, 'JPEG', quality=40)
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name="OBC_Form_VIII_Filled.jpg")