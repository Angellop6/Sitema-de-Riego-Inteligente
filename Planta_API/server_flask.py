from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, flash
from werkzeug.utils import secure_filename
import os

# Config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = 'cambia_esto_por_una_clave_secreta'  # cambia en producción

# Simple mobile-friendly HTML template (uses render_template_string for single-file)
HTML_TEMPLATE = '''
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Subir imagen</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial; padding: 1rem; }
    .container { max-width: 520px; margin: 0 auto; }
    .card { border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 1rem; }
    input[type=file] { width: 100%; padding: .5rem 0; }
    button { width: 100%; padding: .75rem; border: none; border-radius: 8px; font-size: 1rem; }
    .success { color: green; }
    .error { color: red; }
    .thumb { max-width: 100%; height: auto; border-radius: 8px; }
    ul { padding-left: 1rem; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Subir imagen desde el teléfono</h2>
    <div class="card">
      {% with messages = get_flashed_messages(category_filter=["error"]) %}
        {% if messages %}
          <div class="error">{{ messages[0] }}</div>
        {% endif %}
      {% endwith %}
      {% with messages = get_flashed_messages(category_filter=["success"]) %}
        {% if messages %}
          <div class="success">{{ messages[0] }}</div>
        {% endif %}
      {% endwith %}

      <form method="post" enctype="multipart/form-data" action="{{ url_for('upload') }}">
        <!-- accept image types and use capture to let mobile open camera if desired -->
        <input type="file" name="file" accept="image/*" required>
        <br><br>
        <button type="submit">Subir imagen</button>
      </form>
    </div>

    <h3>Imágenes subidas</h3>
    <div class="card">
      {% if files|length == 0 %}
        <p>No hay imágenes todavía.</p>
      {% else %}
        <ul>
          {% for f in files %}
            <li>
              <a href="{{ url_for('uploaded_file', filename=f) }}" target="_blank">{{ f }}</a>
            </li>
          {% endfor %}
        </ul>
      {% endif %}
    </div>
  </div>
</body>
</html>
'''


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
    return render_template_string(HTML_TEMPLATE, files=files)


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No se encontró el archivo en la solicitud.', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo.', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # If file exists, add a counter to the filename
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(save_path):
            filename = f"{base}_{counter}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1

        file.save(save_path)
        flash(f'Archivo guardado como: {filename}', 'success')
        return redirect(url_for('index'))
    else:
        flash('Tipo de archivo no permitido. Usa png, jpg, jpeg, gif o webp.', 'error')
        return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    # Host 0.0.0.0 hace que sea accesible desde otros dispositivos en la misma red (teléfono)
    print('Iniciando servidor Flask. Carpeta de subida:', app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=5000, debug=True)