from flask import Flask, request, render_template, send_file, Response
from PIL import Image
from pypdf2 import PdfReader
from docx import Document
import os
import requests
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

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
            img = img.convert('RGB') if conversion_type != 'png_to_webp' else img
            if conversion_type == 'jpg_to_png':
                output_path = output_path.replace('.jpg', '.png').replace('.jpeg', '.png')
                img.save(output_path, 'PNG')
            elif conversion_type == 'png_to_jpg':
                output_path = output_path.replace('.png', '.jpg')
                img.save(output_path, 'JPEG', quality=95)
            elif conversion_type == 'webp_to_png':
                output_path = output_path.replace('.webp', '.png')
                img.save(output_path, 'PNG')
            elif conversion_type == 'png_to_webp':
                output_path = output_path.replace('.png', '.webp')
                img.save(output_path, 'WEBP')
            elif conversion_type == 'gif_to_png':
                output_path = output_path.replace('.gif', '.png')
                img.save(output_path, 'PNG')
            elif conversion_type == 'tiff_to_jpg':
                output_path = output_path.replace('.tiff', '.jpg').replace('.tif', '.jpg')
                img.save(output_path, 'JPEG', quality=95)
        elif conversion_type == 'pdf_to_docx':
            pdf = PdfReader(input_path)
            doc = Document()
            for page in pdf.pages:
                doc.add_paragraph(page.extract_text())
            output_path = output_path.replace('.pdf', '.docx')
            doc.save(output_path)
        elif conversion_type == 'docx_to_pdf':
            doc = Document(input_path)
            html_content = "<html><body>"
            for para in doc.paragraphs:
                html_content += f"<p>{para.text}</p>"
            html_content += "</body></html>"
            output_path = output_path.replace('.docx', '.pdf')
            # Simple HTML-to-PDF (requires client-side library or API in production)
            with open(output_path, 'w') as f:
                f.write(html_content)
        elif conversion_type == 'remove_bg':
            api_key = os.getenv('REMOVE_BG_API_KEY', 'YOUR_API_KEY')  # Set in Vercel
            url = 'https://api.remove.bg/v1.0/removebg'
            files = {'image_file': open(input_path, 'rb')}
            headers = {'X-Api-Key': api_key}
            response = requests.post(url, files=files, headers=headers)
            if response.status_code == 200:
                output_path = output_path.rsplit('.', 1)[0] + '_nobg.png'
                with open(output_path, 'wb') as out:
                    out.write(response.content)
            else:
                return f"Background removal failed: {response.text}", 500
        else:
            return "Invalid conversion type", 400

        return send_file(output_path, as_attachment=True, download_name=output_filename)
    except Exception as e:
        return f"Error: {str(e)}", 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
