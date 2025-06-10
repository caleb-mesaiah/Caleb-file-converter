from flask import Flask, request, render_template, send_file
from PIL import Image, ImageEnhance
import os
import requests
import io
import traceback
import logging
import time

app = Flask(__name__, template_folder='.')
UPLOAD_FOLDER = '/tmp/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Template error: {str(e)}")
        return f"Error rendering template: {str(e)}", 500

@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'file' not in request.files:
            logger.error("No file uploaded")
            return "No file uploaded", 400
        file = request.files['file']
        conversion_type = request.form.get('conversion_type', '')
        if file.filename == '':
            logger.error("No file selected")
            return "No file selected", 400
        if not conversion_type:
            logger.error("No conversion type selected")
            return "No conversion type selected", 400

        filename = file.filename.replace(' ', '_').replace('/', '_')
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        output_filename = 'converted_' + filename
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        # CloudConvert API setup
        cloudconvert_api_key = os.getenv('CLOUDCONVERT_API_KEY', '')
        if not cloudconvert_api_key:
            logger.error("CloudConvert API key missing")
            return "CloudConvert API key not configured", 500

        # Conversion mapping
        conversion_map = {
            'jpg_to_png': ('jpg', 'png'),
            'png_to_jpg': ('png', 'jpg'),
            'webp_to_png': ('webp', 'png'),
            'png_to_webp': ('png', 'webp'),
            'gif_to_png': ('gif', 'png'),
            'tiff_to_jpg': ('tiff', 'jpg'),
            'pdf_to_docx': ('pdf', 'docx'),
            'docx_to_pdf': ('docx', 'pdf')
        }

        if conversion_type in conversion_map:
            input_format, output_format = conversion_map[conversion_type]
            logger.info(f"Converting {filename} from {input_format} to {output_format}")

            # Create CloudConvert job
            job_response = requests.post(
                'https://api.cloudconvert.com/v2/jobs',
                headers={'Authorization': f'Bearer {cloudconvert_api_key}'},
                json={
                    'tasks': {
                        'import': {
                            'operation': 'import/upload'
                        },
                        'convert': {
                            'operation': 'convert',
                            'input': 'import',
                            'output_format': output_format
                        },
                        'export': {
                            'operation': 'export/url',
                            'input': 'convert'
                        }
                    }
                }
            )
            if job_response.status_code != 201:
                logger.error(f"CloudConvert job creation failed: {job_response.text}")
                return f"CloudConvert API error: {job_response.text}", 500
            job_id = job_response.json()['data']['id']

            # Upload file
            upload_task = next(t for t in job_response.json()['data']['tasks'] if t['name'] == 'import')
            upload_url = upload_task['result']['form']['url']
            with open(input_path, 'rb') as f:
                upload_response = requests.post(upload_url, files={'file': f})
                if upload_response.status_code != 200:
                    logger.error(f"CloudConvert upload failed: {upload_response.text}")
                    return f"File upload to CloudConvert failed: {upload_response.text}", 500

            # Wait for job completion
            while True:
                job_status = requests.get(
                    f'https://api.cloudconvert.com/v2/jobs/{job_id}',
                    headers={'Authorization': f'Bearer {cloudconvert_api_key}'}
                ).json()
                if job_status['data']['status'] in ['finished', 'error']:
                    break
                time.sleep(2)

            if job_status['data']['status'] == 'error':
                logger.error(f"CloudConvert job failed: {job_status}")
                return f"CloudConvert conversion failed: {job_status}", 500

            # Download converted file
            export_task = next(t for t in job_status['data']['tasks'] if t['name'] == 'export')
            file_url = export_task['result']['files'][0]['url']
            output_path = output_path.rsplit('.', 1)[0] + f'.{output_format}'
            output_filename = output_filename.rsplit('.', 1)[0] + f'.{output_format}'
            with open(output_path, 'wb') as out:
                out.write(requests.get(file_url).content)
            logger.info(f"Converted file saved to {output_path}")

        elif conversion_type == 'remove_bg':
            logger.info(f"Removing background for {filename}")
            api_key = os.getenv('REMOVE_BG_API_KEY', '')
            if not api_key:
                logger.error("Remove.bg API key missing")
                return "Remove.bg API key not configured", 500
            url = 'https://api.remove.bg/v1.0/removebg'
            files = {'image_file': open(input_path, 'rb')}
            headers = {'X-Api-Key': api_key}
            response = requests.post(url, files=files, headers=headers, timeout=10)
            if response.status_code == 200:
                output_path = output_path.rsplit('.', 1)[0] + '_nobg.png'
                output_filename = output_filename.rsplit('.', 1)[0] + '_nobg.png'
                with open(output_path, 'wb') as out:
                    out.write(response.content)

                # Auto-enhance image
                img = Image.open(output_path)
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.1)  # +10% brightness
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)  # +20% contrast
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.3)  # +30% sharpness
                img.save(output_path, 'PNG')
                logger.info(f"Enhanced image saved to {output_path}")
            else:
                logger.error(f"Background removal failed: {response.text}")
                return f"Background removal failed: {response.text}", 500
        else:
            logger.error(f"Invalid conversion type: {conversion_type}")
            return "Invalid conversion type", 400

        if not os.path.exists(output_path):
            logger.error(f"Output file not created: {output_path}")
            return "Output file not created", 500
        logger.info(f"Sending converted file: {output_filename}")
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}\n{traceback.format_exc()}")
        return f"Error during conversion: {str(e)}", 500
    finally:
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except:
                pass
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass

if __name__ == '__main__':
    app.run(debug=True)
