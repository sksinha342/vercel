from flask import Flask, render_template, request
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pages.qrgen import generate_qr
from pages.pdfaddpass import protect_pdf
from pages.ratio import ratio_img
from pages.doclike import doclike_img

app = Flask(__name__, template_folder="../templates")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/qrgen', methods=['GET','POST'])
def qr_route():
    if request.method == 'POST':
        data = request.form.get('data')
        return generate_qr(data)
    return render_template('qrgen.html')

@app.route('/resize', methods=['GET','POST'])
def resize():
    if request.method == 'POST':
        return ratio_img()
    return render_template('ratio.html')

@app.route('/imgtopdf', methods=['GET','POST'])
def imgtopdf():
    if request.method == 'POST':
        return doclike_img()
    return render_template('doclike.html')

@app.route('/pdfaddpass', methods=['GET','POST'])
def pdf_route():
    if request.method == 'POST':
        return protect_pdf()
    return render_template('pdfaddpass.html')

# Vercel handler
def handler(request, response):
    return app(request.environ, response.start_response)