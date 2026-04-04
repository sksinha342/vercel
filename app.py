from flask import Flask, render_template, request
import os

# Pages folder se functions import karein
from pages.qrgen import generate_qr
from pages.pdfaddpass import protect_pdf
from pages.ratio import ratio_img
from pages.doclike import doclike_img
app = Flask(__name__)

@app.route('/')
def index():
    # Index page par sabhi tools ki list dikhayenge
    return render_template('index.html')

@app.route('/resize', methods=['GET', 'POST'])
def resize():
    if request.method == 'POST':
        # Yahan argument pass karne ki zaroorat nahi hai
        return ratio_img() 
    return render_template('ratio.html')
@app.route('/imgtopdf', methods=['GET', 'POST'])
def imgtopdf():
    if request.method == 'POST':
        
        return doclike_img()
    return render_template('doclike.html')

# app.py ke end
if __name__ == '__main__':
    app.run(debug=True)