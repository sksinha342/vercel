from flask import Flask, render_template, request, send_file
import io, json, cv2
import numpy as np
from PIL import Image
import img2pdf

'''app = Flask(__name__)

@app.route('/')
def index():
    return render_template('doclike.html')

@app.route('/edit', methods=['POST'])
'''
def doclike_img():
    file = request.files['image']
    points = json.loads(request.form.get('points'))
    rotate_angle = int(request.form.get('rotate', 0))
    target_kb = request.form.get('target_kb')
    as_pdf = request.form.get('as_pdf') == 'true'

    # OpenCV Processing
    in_memory_file = io.BytesIO()
    file.save(in_memory_file)
    data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)

    # Perspective Wrap
    pts1 = np.float32([[p['x'], p['y']] for p in points])
    width = int(max(np.linalg.norm(pts1[0]-pts1[1]), np.linalg.norm(pts1[2]-pts1[3])))
    height = int(max(np.linalg.norm(pts1[0]-pts1[3]), np.linalg.norm(pts1[1]-pts1[2])))
    pts2 = np.float32([[0,0], [width,0], [width,height], [0,height]])
    
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    result = cv2.warpPerspective(img, matrix, (width, height))
    
    # Convert to PIL
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(result_rgb)

    if rotate_angle != 0:
        pil_img = pil_img.rotate(rotate_angle, expand=True)

    # KB Optimization
    img_io = io.BytesIO()
    quality = 95
    pil_img.save(img_io, 'JPEG', quality=quality)
    
    if target_kb and target_kb.isdigit():
        while img_io.tell() > int(target_kb)*1024 and quality > 10:
            img_io.seek(0); img_io.truncate()
            quality -= 5
            pil_img.save(img_io, 'JPEG', quality=quality)

    img_io.seek(0)

    if as_pdf:
        pdf_io = io.BytesIO()
        # Direct bytes se PDF banana
        pdf_bytes = img2pdf.convert(img_io.getvalue())
        pdf_io.write(pdf_bytes)
        pdf_io.seek(0)
        return send_file(pdf_io, mimetype='application/pdf')
    
    return send_file(img_io, mimetype='image/jpeg')

'''if __name__ == '__main__':
    app.run(debug=True)
'''