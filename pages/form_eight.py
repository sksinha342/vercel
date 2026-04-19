import os
import uuid
import random
from flask import Blueprint, render_template, request, send_file, current_app
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime



import threading
import time

def delete_file_after_delay(file_path, delay=60):
    """60 सेकंड बाद फाइल डिलीट करने का फंक्शन"""
    def delay_delete():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Deleted temporary file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting file: {e}")

    # बैकग्राउंड में थ्रेड चलाना ताकि यूजर को इंतज़ार न करना पड़े
    threading.Thread(target=delay_delete, daemon=True).start()



# 1. Blueprint Setup (मुख्य ऐप के साथ जोड़ने के लिए)
form_eight_bp = Blueprint('form_eight', __name__)

# टूल की जानकारी (मुख्य पेज पर दिखने के लिए)
metadata = {
    "title": "OBC Form VIII Generator",
    "description": "Handwriting style Hindi form filler for OBC certificates.",
    "image": "pages/form8.jpg" # अपनी इमेज का नाम दें
}

BASE_IMAGE_PATH = "form_viii_base.jpg" # सुनिश्चित करें कि यह फ़ाइल मुख्य डायरेक्टरी में हो

def get_hindi_font(size=28):
    font_paths = [
        "fonts/Kalam-Regular.ttf",
        "fonts/Mukta-Regular.ttf",
        "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/Mangal.ttf",
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

# 2. Routes (Blueprint का उपयोग करते हुए)
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
    
    # मुख्य ऐप के अपलोड फोल्डर का रास्ता
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

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
    
    final_img = img.convert('RGB')
    output_filename = f"form_filled_{uuid.uuid4().hex}.jpg"
    output_path = os.path.join(upload_folder, output_filename)
    final_img.save(output_path, quality=40)
    
    delete_file_after_delay(output_path, delay=1060)
    return send_file(output_path, as_attachment=True, download_name="OBC_Form_VIII_Filled.jpg")