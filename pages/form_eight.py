import os
import io
import random
from flask import Blueprint, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont

form_eight_bp = Blueprint('form_eight', __name__)

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_IMAGE_PATH = os.path.join(BASE_DIR, "form_viii_base.jpg")

def get_font(size=28):
    # 'Mukta' सबसे एडवांस हिंदी फोंट है रेंडरिंग के मामले में
    p = os.path.join(BASE_DIR, "fonts", "Mukta-Regular.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def render_advanced_text(base_img, text, x, y, font_size=28, color="darkblue", rotate=0):
    """
    यह फंक्शन एक अलग 'Canvas' पर टेक्स्ट लिखता है और फिर उसे बेस इमेज पर पेस्ट करता है।
    इससे Linux के रेंडरिंग इंजन को पूरे शब्द को प्रोसेस करने का मौका मिलता है।
    """
    if not text: return
    
    font = get_font(font_size)
    # एक बड़ा ट्रांसपेरेंट कैनवास बनाएँ
    text_canvas = Image.new('RGBA', (1000, 200), (255, 255, 255, 0))
    draw_canvas = ImageDraw.Draw(text_canvas)
    
    # 🌟 CRITICAL FIX: यहाँ 'शून्य' को पूरे शब्द की तरह रेंडर कर रहे हैं
    draw_canvas.text((20, 50), str(text), font=font, fill=color)
    
    # फालतू खाली जगह हटाएँ (Autocrop)
    bbox = text_canvas.getbbox()
    if bbox:
        text_canvas = text_canvas.crop(bbox)
    
    # रोटेशन (सिर्फ Income के लिए)
    if rotate != 0:
        text_canvas = text_canvas.rotate(rotate, expand=True, resample=Image.BICUBIC)
    
    # असली इमेज पर पेस्ट करें
    base_img.paste(text_canvas, (x, y), text_canvas)

@form_eight_bp.route('/form_eight/generate', methods=['POST'])
def generate():
    data = request.form.to_dict()
    img = Image.open(BASE_IMAGE_PATH).convert('RGBA')
    
    # 1. नाम, गाँव आदि के लिए (Normal Rendering)
    # यहाँ x, y वही रखो जो पहले थे
    render_advanced_text(img, data.get('name', ''), 210, 245)
    render_advanced_text(img, data.get('village', ''), 240, 285)
    
    # 2. 🔥 INCOME के लिए (The Advanced Fix)
    if data.get('annual_income'):
        # यहाँ शून्य एकदम सही रेंडर होगा
        render_advanced_text(img, data['annual_income'], 710, 835, font_size=30)
    
    if data.get('total_income'):
        # रोटेशन के साथ
        render_advanced_text(img, data['total_income'], 122, 915, font_size=26, rotate=2.5)

    # 3. Save to Buffer
    img_io = io.BytesIO()
    img.convert('RGB').save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name="OBC_Form.jpg")