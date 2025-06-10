from flask import Flask, request, render_template, send_file
from PIL import Image
from pypdf2 import PdfReader
from docx import Document
from rembg import remove
import pdfkit
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')  # No templates/ folder

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return "No file uploaded", 400
    file = request.files['file']
    conversion_type = request.form['conversion_type']
    if file.filename == '':
        return "No file selected", 400

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(input_path)
    output_filename = 'converted_' + file.filename
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

    try:
        if conversion_type in ['jpg_to_png', 'png_to_jpg', 'webp_to_png', 'png_to_webp', 'gif_to_png', 'tiff_to_jpg']:
            img = Image.open(input_path)
            img = img.convertTypical Response: