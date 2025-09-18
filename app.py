from flask import Flask, render_template, request, redirect, url_for, session, make_response
import os
from werkzeug.utils import secure_filename
from docx import Document
import pytesseract
from PIL import Image
import PyPDF2
import speech_recognition as sr
from pydub import AudioSegment
from moviepy import VideoFileClip
from langdetect import detect
from deep_translator import GoogleTranslator
from datetime import datetime

import sqlite3
from flask import Flask, render_template, request
from datetime import datetime

# Ensure history table exists
def init_db():
    conn = sqlite3.connect('smartdoc_data.db')
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        analysis_date TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

# Call it once when the app starts
init_db()
def save_history(file_name, file_type):
    conn = sqlite3.connect('smartdoc_data.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO history (file_name, file_type, analysis_date) VALUES (?, ?, ?)",
        (file_name, file_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    print(f"Inserted into history: {file_name} ({file_type})")
app = Flask(__name__)

app = Flask(__name__)
app.secret_key = 'sigma_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg', 'mp3', 'wav', 'mp4', 'mkv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR'

def detect_and_translate(text):
    try:
        lang = detect(text)
        if lang != 'en':
            return GoogleTranslator(source='auto', target='en').translate(text)
        return text
    except Exception as e:
        return f"\u26a0\ufe0f Translation failed: {str(e)}"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def video_to_text(video_path):
    try:
        temp_audio = "temp_audio.wav"
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(temp_audio)
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_audio) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
    except Exception as e:
        return f"\u274c Video processing failed: {str(e)}"

def clean_text_for_xml(text):
    # Remove characters not allowed in XML
    valid_chars = []
    for char in text:
        if ord(char) in (0x09, 0x0A, 0x0D) or (0x20 <= ord(char) <= 0xD7FF) or (0xE000 <= ord(char) <= 0xFFFD):
            valid_chars.append(char)
        else:
            valid_chars.append(' ')  # Replace with space or you can use ''
    return ''.join(valid_chars)


def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(audio_path)
    audio.export("converted.wav", format="wav")
    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        except Exception as e:
            return f"\u26a0\ufe0f Audio transcription failed: {str(e)}"

def extract_text(file_path, ext):
    raw_text = ""
    try:
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                raw_text = ''.join(file.readlines())
        elif ext == 'docx':
            doc = Document(file_path)
            raw_text = '\n'.join([para.text for para in doc.paragraphs])
        elif ext == 'pdf':
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                raw_text = ''
                for page in reader.pages:
                    page_text = page.extract_text() or ''
                    raw_text += clean_text_for_xml(page_text) + '\n'
        elif ext in {'png', 'jpg', 'jpeg'}:
            image = Image.open(file_path)
            raw_text = pytesseract.image_to_string(image)
        elif ext in {'mp3', 'wav'}:
            raw_text = transcribe_audio(file_path)
        elif ext in {'mp4', 'mkv'}:
            raw_text = video_to_text(file_path)
        else:
            raise ValueError("Unsupported file extension.")
    except Exception as e:
        return f"\u274c Extraction failed: {str(e)}"
    return detect_and_translate(raw_text)


def save_to_docx_file(filename, text):
    base = os.path.splitext(filename)[0]
    doc = Document()
    doc.add_heading(f'Extracted Content: {filename}', 0)
    doc.add_paragraph(text)
    path = os.path.join(OUTPUT_FOLDER, f"{base}.docx")
    doc.save(path)

def clear_upload_folder():
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))

@app.route('/')
def index():
    # Fetch last 5 uploads from history
    conn = sqlite3.connect('smartdoc_data.db')
    cur = conn.cursor()
    cur.execute("SELECT file_name, file_type, analysis_date FROM history ORDER BY analysis_date DESC LIMIT 5")
    recent_files = cur.fetchall()
    conn.close()

    return render_template('upload.html', recent_files=recent_files)

@app.route('/history')
def history():
    conn = sqlite3.connect('smartdoc_data.db')
    cur = conn.cursor()
    cur.execute("SELECT file_name, file_type, analysis_date FROM history ORDER BY analysis_date DESC")
    history_data = cur.fetchall()
    conn.close()
    return render_template('history.html', history=history_data)

@app.route('/', methods=['GET', 'POST'])
def home():
    global file_contents
    file_contents = []  # 💣 Wipe previous global data

    if request.method == 'POST':
        # 🔥 Start with a clean state
        session.clear()

        session['file_contents'] = []
        session['errors'] = []
        session.modified = True

        uploaded_files = request.files.getlist('files')
        output_lang = request.form.get('lang', 'original')

        if not uploaded_files or uploaded_files[0].filename == '':
            session['errors'].append("⚠️ No files selected.")
            return redirect(url_for('results'))

        errors = []

        for idx, file in enumerate(uploaded_files):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower()
                unique_name = f"{filename.rsplit('.', 1)[0]}_{idx}.{ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(file_path)

                try:
                    text = extract_text(file_path, ext)

                    if output_lang != 'original':
                        try:
                            detected_lang = detect(text)
                            if detected_lang != output_lang:
                                text = GoogleTranslator(source='auto', target=output_lang).translate(text)
                        except Exception as e:
                            text += f"\n⚠️ Translation Error: {str(e)}"

                    save_to_docx_file(unique_name, text)
                    file_contents.append({
                        'filename': unique_name,
                        'content': text,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                except Exception as e:
                    errors.append(f"❌ {filename} failed: {str(e)}")
            else:
                errors.append(f"❌ {file.filename} not allowed.")

        # 💾 Update session freshly
        session['file_contents'] = file_contents
        session['errors'] = errors
        return redirect(url_for('results'))

    return render_template('upload.html')

@app.route('/results')
def results():
    file_contents = session.get('file_contents')
    errors = session.get('errors')

    if not file_contents:
        print("⚠️ Session lost or file_contents missing.")
        file_contents = []
        errors = errors if errors else ["⚠️ No files were processed. Please try again."]

    # ✅ Debug print (see your terminal for this)
    print("🧾 File contents loaded in session:", file_contents)

    response = make_response(render_template('results.html', file_contents=file_contents, errors=errors))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response
app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return "No file uploaded", 400

    file_contents = []

    for file in files:
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].replace('.', '')

        # Save file
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        # Read content (text files only)
        try:
            file.seek(0)  # Reset pointer
            content = file.read().decode('utf-8')
        except:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        # Add to list
        file_contents.append({
            "filename": filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": content
        })

        # Save history
        save_history(filename, file_ext)

    return render_template('results.html', file_contents=file_contents)

@app.errorhandler(413)
def too_large(e):
    return "File too large. Maximum allowed size is 100MB.", 413

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)