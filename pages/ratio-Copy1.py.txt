from flask import Flask, render_template, request, send_file
import io
from PIL import Image

'''app = Flask(__name__)

@app.route('/')
def index():
    return render_template('ratio.html')

@app.route('/edit', methods=['POST'])

'''
def ratio_img():
    file = request.files['image']
    target_kb = request.form.get('target_kb')
    
    img = Image.open(file.stream)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img_io = io.BytesIO()
    
    if target_kb and target_kb.isdigit():
        target_bytes = int(target_kb) * 1024
        quality = 95
        img.save(img_io, 'JPEG', quality=quality)
        
        # Binary search for quality to be faster
        while img_io.tell() > target_bytes and quality > 10:
            img_io.seek(0)
            img_io.truncate()
            quality -= 5
            img.save(img_io, 'JPEG', quality=quality)
    else:
        img.save(img_io, 'JPEG', quality=95)
    
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

''' if __name__ == '__main__':
    app.run(debug=True, port=5000
'''