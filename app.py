# app.py (updated v2)
import os
import io
import base64
import sqlite3
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash, jsonify
from werkzeug.utils import secure_filename
from model import analyze_image, analyze_image_bytes, annotate_image_on_disk
import logging

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'emotion_app.db')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_env(key, default=None):
    return os.environ.get(key, default)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DATABASE'] = DB_PATH
app.secret_key = get_env('FLASK_SECRET_KEY', 'akinde_secret_for_dev_v2')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('emotion_app_v2')

# Database helpers
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            filename TEXT,
            annotated_filename TEXT,
            emotion TEXT,
            emotions_json TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_submission(name, email, filename, annotated_filename, emotion, emotions_json):
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''
        INSERT INTO submissions (name, email, filename, annotated_filename, emotion, emotions_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, email, filename, annotated_filename, emotion, emotions_json, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def query_submissions(limit=100):
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('SELECT id, name, email, filename, annotated_filename, emotion, emotions_json, created_at FROM submissions ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# Utility
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()

        # handle file upload first
        if 'photo' in request.files and request.files['photo'].filename != '':
            file = request.files['photo']
            if not allowed_file(file.filename):
                flash('File type not allowed. Allowed: png,jpg,jpeg,gif', 'error')
                return redirect(url_for('index'))
            filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{file.filename}")
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            try:
                analysis = analyze_image(save_path)
            except Exception as e:
                logger.exception('DeepFace failed on uploaded image: %s', e)
                return render_template('error.html', message='Model error: could not analyze the uploaded image. Try a different image or check your environment.'), 500

        # handle webcam base64
        elif request.form.get('webcam_data'):
            webcam_b64 = request.form.get('webcam_data', '')
            if ',' in webcam_b64:
                header, encoded = webcam_b64.split(',', 1)
            else:
                encoded = webcam_b64
            try:
                file_bytes = base64.b64decode(encoded)
            except Exception as e:
                logger.exception('Invalid webcam data: %s', e)
                flash('Invalid webcam image data. Please try again.', 'error')
                return redirect(url_for('index'))

            filename = f"webcam_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.png"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(save_path, 'wb') as f:
                f.write(file_bytes)
            try:
                analysis = analyze_image_bytes(file_bytes)
            except Exception as e:
                logger.exception('DeepFace failed on webcam image: %s', e)
                return render_template('error.html', message='Model error: could not analyze the webcam image. Try again.'), 500
        else:
            flash('No image provided. Upload a file or capture from webcam.', 'error')
            return redirect(url_for('index'))

        dominant = analysis.get('dominant_emotion', 'unknown')
        emotions = analysis.get('emotion', {})

        # annotate image (draw label) - returns relative filename for annotated image
        try:
            annotated_filename = annotate_image_on_disk(save_path, dominant)
        except Exception as e:
            logger.exception('Failed to annotate image: %s', e)
            annotated_filename = filename  # fallback to original

        try:
            save_submission(name, email, filename, annotated_filename, dominant, str(emotions))
        except Exception as e:
            logger.exception('Failed to save submission to DB: %s', e)

        return render_template('result.html',
                               filename=annotated_filename,
                               dominant_emotion=dominant,
                               emotions=emotions)

    except Exception as e:
        logger.exception('Error in /analyze: %s', e)
        return render_template('error.html', message='Unexpected server error. Check server logs.'), 500

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)

@app.route('/history')
def history():
    try:
        rows = query_submissions(limit=500)
        return render_template('history.html', rows=rows)
    except Exception as e:
        logger.exception('Failed to fetch history: %s', e)
        return render_template('error.html', message='Unable to load history.'), 500

@app.route('/download_history')
def download_history():
    import csv
    from flask import Response
    rows = query_submissions(limit=1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Name','Email','Filename','AnnotatedFilename','Emotion','Timestamp'])
    for r in rows:
        writer.writerow([r[0],r[1],r[2],r[3],r[4],r[5],r[7]])
    output.seek(0)
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment; filename=history.csv"})

@app.route('/health')
def health():
    return jsonify(status='ok', time=datetime.utcnow().isoformat())

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message='Page not found (404)'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', message='Server error (500)'), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
