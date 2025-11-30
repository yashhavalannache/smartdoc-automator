# from flask import Flask, render_template, request, redirect, url_for, session, make_response, send_file, flash
# import os
# from werkzeug.utils import secure_filename
# from docx import Document
# import PyPDF2
# import speech_recognition as sr
# from pydub import AudioSegment
# from moviepy import VideoFileClip
# from langdetect import detect
# from deep_translator import GoogleTranslator
# from datetime import datetime
# import sqlite3
# from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
# import threading
# import json
# import io
# import whisper
# import easyocr
# from pptx import Presentation
# from PIL import Image, ImageFilter, ImageEnhance, ImageOps
# import numpy as np
# from paddleocr import PaddleOCR
# import tempfile
# import time
# import math

# # ---------------- Database Setup ---------------- #
# def init_db():
#     conn = sqlite3.connect('smartdoc_data.db')
#     cur = conn.cursor()
#     cur.execute('''
#     CREATE TABLE IF NOT EXISTS history (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         file_name TEXT NOT NULL,
#         file_type TEXT NOT NULL,
#         analysis_date TEXT NOT NULL
#     )
#     ''')
#     conn.commit()
#     conn.close()

# init_db()

# def save_history(file_name, file_type):
#     conn = sqlite3.connect('smartdoc_data.db')
#     cur = conn.cursor()
#     cur.execute(
#         "INSERT INTO history (file_name, file_type, analysis_date) VALUES (?, ?, ?)",
#         (file_name, file_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#     )
#     conn.commit()
#     conn.close()

# # ---------------- Flask Setup ---------------- #
# app = Flask(__name__)
# app.secret_key = 'sigma_secret_key'
# UPLOAD_FOLDER = 'uploads'
# OUTPUT_FOLDER = 'output'
# ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'pptx', 'png', 'jpg', 'jpeg', 'mp3', 'wav', 'mp4', 'mkv'}
# MAX_SIZE_MB = 300

# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = MAX_SIZE_MB * 1024 * 1024
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# # ---------------- OCR Setup ---------------- #
# reader_pool = {}
# paddle_pool = {}

# def get_easyocr_reader(lang_hint=None):
#     if lang_hint in ['hi', 'mr']:
#         key = 'hi_mr'; langs = ['en', 'hi']
#     elif lang_hint == 'kn':
#         key = 'kn'; langs = ['kn', 'en']
#     elif lang_hint == 'ta':
#         key = 'ta'; langs = ['ta', 'en']
#     else:
#         key = 'en'; langs = ['en']

#     if key not in reader_pool:
#         try:
#             reader_pool[key] = easyocr.Reader(langs, gpu=False)
#         except Exception as e:
#             print(f"[EasyOCR Init Error for {langs}] -> {e}")
#             reader_pool[key] = easyocr.Reader(['en'], gpu=False)
#     return reader_pool[key]

# def get_paddle_ocr(lang_hint=None):
#     key = lang_hint or 'en'
#     if key not in paddle_pool:
#         try:
#             paddle_pool[key] = PaddleOCR(use_angle_cls=True, lang='en')
#         except Exception as e:
#             print(f"[PaddleOCR Init Error for {key}] -> {e}")
#             paddle_pool[key] = PaddleOCR(use_angle_cls=True, lang='en')
#     return paddle_pool[key]

# # ---------------- Utility Functions ---------------- #
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def clean_text_for_xml(text):
#     return ''.join(ch if ord(ch) in (0x09,0x0A,0x0D) or (0x20 <= ord(ch) <= 0xD7FF) or (0xE000 <= ord(ch) <= 0xFFFD) else ' ' for ch in text)

# def safe_delete(path):
#     try:
#         if path and os.path.exists(path):
#             os.remove(path)
#     except Exception:
#         pass

# # ---------------- Image Preprocessing ---------------- #
# def preprocess_image(image_path, max_dim=1600):
#     try:
#         img = Image.open(image_path).convert('RGB')
#     except Exception:
#         return image_path

#     w, h = img.size
#     if max(w, h) > max_dim:
#         ratio = max_dim / float(max(w, h))
#         img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

#     # Enhance contrast & sharpness
#     img = ImageEnhance.Contrast(img).enhance(1.5)
#     img = ImageEnhance.Sharpness(img).enhance(1.2)

#     # Convert to grayscale and denoise
#     gray = img.convert('L')
#     np_img = np.array(gray)

#     # Adaptive threshold (binarization)
#     mean = np.mean(np_img)
#     binary = np.where(np_img > mean, 255, 0).astype(np.uint8)

#     # Slight dilation + erosion to unify text edges
#     from scipy.ndimage import binary_dilation, binary_erosion
#     binary = binary_dilation(binary, iterations=1)
#     binary = binary_erosion(binary, iterations=1)

#     final_img = Image.fromarray(binary.astype(np.uint8) * 255)
#     final_img = ImageOps.autocontrast(final_img)

#     temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
#     final_img.save(temp_file.name, format='PNG', optimize=True)
#     return temp_file.name

# def is_blank_image(image_path, threshold=0.95):
#     try:
#         img = Image.open(image_path).convert("L")
#         arr = np.array(img) / 255.0
#         white_fraction = float(np.mean(arr > 0.95))
#         return white_fraction >= threshold
#     except Exception:
#         return False

# # ---------------- OCR Engines ---------------- #
# def run_easyocr(path, lang_hint='en'):
#     try:
#         reader = get_easyocr_reader(lang_hint)
#         res = reader.readtext(path, detail=0, paragraph=True)
#         return "\n".join(res).strip() if res else ""
#     except Exception:
#         return ""

# def run_paddleocr(path, lang_hint='en'):
#     try:
#         ocr = get_paddle_ocr(lang_hint)
#         raw = ocr.ocr(path, cls=True)
#         lines = []
#         for page in raw:
#             for item in page:
#                 try:
#                     lines.append(item[1][0])
#                 except Exception:
#                     continue
#         return "\n".join(lines).strip()
#     except Exception:
#         return ""

# def choose_best_candidate(*cands):
#     best = ""
#     best_score = -1
#     for t in cands:
#         if not t:
#             continue
#         alpha = sum(1 for c in t if c.isalpha())
#         score = alpha + min(len(t), 200) / 10.0
#         if score > best_score:
#             best_score = score
#             best = t
#     return best.strip()

# # ---------------- Safe Translation ---------------- #
# def safe_translate_text(text, target_lang, timeout=12, chunk_size=3000):
#     if not text or target_lang == 'original':
#         return text

#     chunks = []
#     i = 0
#     n = len(text)
#     while i < n:
#         end = min(i + chunk_size, n)
#         if end < n:
#             j = end
#             limit = min(n, end + 200)
#             while j < limit and text[j] not in ("\n", " "):
#                 j += 1
#             if j < limit:
#                 end = j
#         chunks.append(text[i:end])
#         i = end

#     translated_chunks = []
#     for chunk in chunks:
#         with ThreadPoolExecutor(max_workers=1) as exec:
#             fut = exec.submit(lambda: GoogleTranslator(source='auto', target=target_lang).translate(chunk))
#             try:
#                 translated_chunks.append(fut.result(timeout=timeout))
#             except TimeoutError:
#                 warning = f"\n\n⚠️ Translation timed out after {timeout}s for a chunk.\n\n"
#                 untranslated = text[text.find(chunk):]
#                 return ("".join(translated_chunks) + warning + untranslated) if translated_chunks else (warning + text)
#             except Exception as e:
#                 translated_chunks.append(chunk + f"\n\n⚠️ Translation failed: {e}\n\n")
#     return "\n".join(translated_chunks)

# # ---------------- Image Extraction ---------------- #
# def extract_text_from_image(image_path):
#     if is_blank_image(image_path):
#         return "⚠️ No readable text found (image appears blank)."

#     prepped = preprocess_image(image_path)

#     lang_candidates = ['en', 'hi', 'mr', 'kn', 'ta']
#     detected_lang = 'en'
#     best_text = ''
#     best_score = 0

#     for lang in lang_candidates:
#         try:
#             text_easy = run_easyocr(prepped, lang_hint=lang)
#             text_paddle = run_paddleocr(prepped, lang_hint=lang)
#             merged = choose_best_candidate(text_easy, text_paddle)
#             score = sum(1 for c in merged if c.isalpha())
#             if score > best_score:
#                 best_score = score
#                 best_text = merged
#                 detected_lang = lang
#         except Exception:
#             continue

#     safe_delete(prepped)

#     if not best_text:
#         return "⚠️ No readable content detected."

#     return best_text.strip()

# # ---------------- Audio & Video ---------------- #
# def audio_to_text(audio_path, whisper_model_name="tiny"):
#     tmp_wav = None
#     try:
#         if not audio_path.lower().endswith('.wav'):
#             sound = AudioSegment.from_file(audio_path)
#             sound = sound.set_frame_rate(16000).set_channels(1)
#             tmp_wav = audio_path.rsplit('.', 1)[0] + "_converted.wav"
#             sound.export(tmp_wav, format='wav')
#             work_path = tmp_wav
#         else:
#             work_path = audio_path

#         model = whisper.load_model(whisper_model_name)
#         audio = AudioSegment.from_wav(work_path)
#         duration_s = len(audio) / 1000.0

#         if duration_s <= 60:
#             result = model.transcribe(work_path, verbose=False, fp16=False)
#             return result.get("text", "").strip()

#         chunk_ms = 60 * 1000
#         chunks = []
#         for start_ms in range(0, len(audio), chunk_ms):
#             end_ms = min(start_ms + chunk_ms, len(audio))
#             chunk = audio[start_ms:end_ms]
#             chunk_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
#             chunk.export(chunk_file.name, format="wav")
#             chunks.append(chunk_file.name)

#         def transcribe_chunk(path):
#             try:
#                 res = model.transcribe(path, verbose=False, fp16=False)
#                 return res.get("text", "").strip()
#             except Exception:
#                 return "[unrecognized]"

#         texts = []
#         with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as exec:
#             for fut in as_completed(exec.submit(transcribe_chunk, c) for c in chunks):
#                 texts.append(fut.result())

#         for c in chunks:
#             safe_delete(c)

#         return " ".join(texts).strip()

#     except Exception as e:
#         print("⚠️ Whisper error:", str(e))
#         try:
#             recognizer = sr.Recognizer()
#             with sr.AudioFile(audio_path) as source:
#                 audio_data = recognizer.record(source)
#                 return recognizer.recognize_google(audio_data)
#         except Exception:
#             return "⚠️ Audio could not be transcribed."
#     finally:
#         if tmp_wav:
#             safe_delete(tmp_wav)

# def video_to_text(video_path):
#     try:
#         temp_audio = "temp_audio.wav"
#         clip = VideoFileClip(video_path)
#         clip.audio.write_audiofile(temp_audio, logger=None)

#         recognizer = sr.Recognizer()
#         with sr.AudioFile(temp_audio) as source:
#             recognizer.adjust_for_ambient_noise(source, duration=0.2)
#         with sr.AudioFile(temp_audio) as source:
#             audio_data = recognizer.record(source)
#             text = recognizer.recognize_google(audio_data)
#         return text.strip()
#     except Exception as e:
#         return f"❌ Video processing failed: {str(e)}"

# # ---------------- Save to DOCX ---------------- #
# def save_to_docx_file(filename, text):
#     base = os.path.splitext(filename)[0]
#     doc = Document()
#     doc.add_heading(f'Extracted Content: {filename}', 0)
#     for line in text.splitlines():
#         if line.strip():
#             doc.add_paragraph(line.strip())
#     path = os.path.join(OUTPUT_FOLDER, f"{base}.docx")
#     doc.save(path)

# # ---------------- Extract text by type ---------------- #
# def extract_text_only(file_path, ext, output_lang='original'):
#     try:
#         ext = ext.lower()
#         extracted = ""

#         if ext == 'txt':
#             with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
#                 extracted = f.read().rstrip()
#         elif ext == 'docx':
#             doc = Document(file_path)
#             extracted = '\n'.join([p.text for p in doc.paragraphs])
#         elif ext == 'pdf':
#             text = ""
#             with open(file_path, 'rb') as f:
#                 reader_pdf = PyPDF2.PdfReader(f)
#                 for page in reader_pdf.pages:
#                     try:
#                         page_text = page.extract_text() or ''
#                     except Exception:
#                         page_text = ''
#                     text += clean_text_for_xml(page_text) + '\n\n'
#             extracted = text.strip()
#         elif ext == 'pptx':
#             prs = Presentation(file_path)
#             slide_texts = []
#             for idx, slide in enumerate(prs.slides, 1):
#                 slide_lines = [shape.text.strip() for shape in slide.shapes if hasattr(shape, 'text')]
#                 slide_texts.append(f"--- Slide {idx} ---\n" + ("\n".join(slide_lines)))
#             extracted = "\n\n".join(slide_texts)
#         elif ext in {'png', 'jpg', 'jpeg'}:
#             extracted = extract_text_from_image(file_path)
#         elif ext in {'mp3', 'wav'}:
#             extracted = audio_to_text(file_path)
#         elif ext in {'mp4', 'mkv'}:
#             extracted = video_to_text(file_path)
#         else:
#             return "❌ Unsupported file type."

#         if not extracted:
#             return "⚠️ No readable content detected."

#         if output_lang != 'original':
#             try:
#                 translated = safe_translate_text(extracted, output_lang, timeout=12, chunk_size=3000)
#                 return translated
#             except Exception as e:
#                 return extracted + f"\n\n⚠️ Translation failed: {str(e)}"

#         return extracted

#     except Exception as e:
#         return f"❌ Extraction failed: {str(e)}"

# # ---------------- Routes ---------------- #
# @app.route('/', methods=['GET', 'POST'])
# def home():
#     if request.method == 'POST':
#         session.clear()
#         uploaded_files = request.files.getlist('files')
#         output_lang = request.form.get('lang', 'original')
#         errors = []
#         result_keys = []

#         if not uploaded_files or uploaded_files[0].filename == '':
#             session['errors'] = ["⚠️ No files selected."]
#             return redirect(url_for('results'))

#         lock = threading.Lock()
#         with ThreadPoolExecutor(max_workers=3) as executor:
#             future_to_file = {}
#             for idx, file in enumerate(uploaded_files):
#                 if file and allowed_file(file.filename):
#                     filename = secure_filename(file.filename)
#                     ext = filename.rsplit('.', 1)[1].lower()
#                     unique_name = f"{os.path.splitext(filename)[0]}_{idx}_{int(datetime.now().timestamp())}.{ext}"
#                     file_path = os.path.join(UPLOAD_FOLDER, unique_name)
#                     file.save(file_path)
#                     future = executor.submit(extract_text_only, file_path, ext, output_lang)
#                     future_to_file[future] = (unique_name, ext)
#                 else:
#                     errors.append(f"❌ {file.filename} not allowed.")

#             for future in as_completed(future_to_file):
#                 unique_name, ext = future_to_file[future]
#                 raw_text = future.result()
#                 text = raw_text
#                 save_to_docx_file(unique_name, text)
#                 save_history(unique_name, ext)
#                 result_obj = {
#                     'filename': unique_name,
#                     'content': text,
#                     'timestamp': datetime.now().strftime('%d %b %Y, %I:%M %p')
#                 }
#                 json_path = os.path.join(OUTPUT_FOLDER, f"{unique_name}.json")
#                 with open(json_path, 'w', encoding='utf-8') as jf:
#                     json.dump(result_obj, jf, ensure_ascii=False, indent=2)
#                 with lock:
#                     result_keys.append(unique_name)

#         session['file_keys'] = result_keys
#         session['errors'] = errors
#         session.modified = True
#         return redirect(url_for('results'))

#     conn = sqlite3.connect('smartdoc_data.db')
#     cur = conn.cursor()
#     cur.execute("SELECT file_name, file_type, analysis_date FROM history ORDER BY analysis_date DESC LIMIT 5")
#     recent_files = cur.fetchall()
#     conn.close()
#     return render_template('upload.html', recent_files=recent_files)

# @app.route('/results')
# def results():
#     result_keys = session.get('file_keys', [])
#     errors = session.get('errors', [])
#     file_contents = []

#     for key in result_keys:
#         json_file = os.path.join(OUTPUT_FOLDER, f"{key}.json")
#         if os.path.exists(json_file):
#             with open(json_file, 'r', encoding='utf-8') as f:
#                 file_contents.append(json.load(f))

#     if not file_contents and not errors:
#         errors = ["⚠️ No files were processed. Please try again."]

#     response = make_response(render_template('results.html', file_contents=file_contents, errors=errors))
#     response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
#     response.headers['Pragma'] = 'no-cache'
#     return response


# @app.route('/download_text/<filename>')
# def download_text(filename):
#     json_path = os.path.join(OUTPUT_FOLDER, f"{filename}.json")
#     if os.path.exists(json_path):
#         with open(json_path, 'r', encoding='utf-8') as f:
#             content = json.load(f)['content']
#         buffer = io.BytesIO()
#         buffer.write(content.encode('utf-8'))
#         buffer.seek(0)
#         return send_file(buffer, as_attachment=True, download_name=f"{filename}_SmartDoc.txt", mimetype='text/plain')
#     else:
#         flash("File not found for download.")
#         return redirect(url_for('results'))

# @app.errorhandler(413)
# def too_large(e):
#     return f"File too large. Maximum allowed size is {MAX_SIZE_MB}MB.", 413

# @app.errorhandler(500)
# def server_error(e):
#     return "⚠️ Something went wrong! Try uploading fewer or smaller files.", 500

# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 5001))
#     app.run(host='0.0.0.0', port=port, debug=False)
