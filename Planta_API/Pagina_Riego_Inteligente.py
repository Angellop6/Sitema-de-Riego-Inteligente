from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, flash
from werkzeug.utils import secure_filename
import os
import requests
import json
import re
from openai import OpenAI
import paho.mqtt.client as mqtt 
from dotenv import load_dotenv
load_dotenv()

# Configuración general
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

API_KEY = os.getenv("PLANTNET_API_KEY")
PROJECT = os.getenv("PLANTNET_PROJECT")
API_ENDPOINT = f"https://my-api.plantnet.org/v2/identify/{PROJECT}?api-key={API_KEY}"

client = OpenAI(
    base_url=os.getenv("HUGGINGFACE_BASE_URL"),
    api_key=os.getenv("HUGGINGFACE_API_KEY")
)

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC")

# Crear y conectar cliente MQTT
mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print(f"📡 Conectado a broker MQTT en {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print("⚠️ No se pudo conectar al broker MQTT:", e)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = 'clave_super_secreta'

# === Función para identificar planta con PlantNet ===
def identificar_planta(img1_path, img2_path):
    with open(img1_path, 'rb') as img1, open(img2_path, 'rb') as img2:
        files = [
            ('images', (img1_path, img1)),
            ('images', (img2_path, img2))
        ]
        data = {'organs': ['flower', 'leaf']}
        response = requests.post(API_ENDPOINT, files=files, data=data)
        result = response.json()

    if response.status_code == 200 and "results" in result and len(result["results"]) > 0:
        plant = result["results"][0]
        nombre_cientifico = plant["species"]["scientificNameWithoutAuthor"]
        nombre_comun = plant["species"].get("commonNames", ["No disponible"])
        probabilidad = round(plant["score"] * 100, 2)
        return {
            "nombre_cientifico": nombre_cientifico,
            "nombre_comun": ', '.join(nombre_comun),
            "probabilidad": probabilidad
        }
    else:
        return None

# === Función para obtener información de cuidado y nombre común en español ===
def obtener_info_cuidado(nombre_planta):
    prompt = f"""
Eres un asistente experto en plantas.
Te daré el nombre científico de una planta.
Tu tarea:
1. Devuelve únicamente un objeto JSON con los siguientes campos:
   - "nombre_comun": el nombre común en español de la planta, o el más usado si no hay traducción exacta.
   - "humidity": porcentaje de humedad ideal.
   - "care": un consejo breve de cuidado en español (una línea).
2. No agregues texto adicional fuera del JSON.

Ejemplo de formato:
{{
  "nombre_comun": "Helecho de Boston",
  "humidity": 60,
  "care": "Mantener en luz indirecta y regar regularmente."
}}

Pregunta: ¿Cuál es el nombre común en español, el nivel de humedad ideal y un consejo de cuidado para la planta {nombre_planta}?
Responde en el formato JSON exacto.
"""
    completion = client.chat.completions.create(
        model="HuggingFaceTB/SmolLM3-3B:hf-inference",
        messages=[{"role": "user", "content": prompt}],
    )

    texto = completion.choices[0].message.content
    patron_json = r'\{.*?\}'
    coincidencias = re.findall(patron_json, texto, re.DOTALL)

    for c in coincidencias:
        try:
            diccionario = json.loads(c)
            # Asegurarse de que tenga los tres campos
            for campo in ["nombre_comun", "humidity", "care"]:
                if campo not in diccionario:
                    diccionario[campo] = "No disponible"
            return diccionario  # Devuelve {"nombre_comun": ..., "humidity": ..., "care": ...}
        except json.JSONDecodeError:
            continue
    return {"nombre_comun": "No disponible", "humidity": "No disponible", "care": "No se pudo obtener información."}

# === HTML Template Mejorado ===
HTML_TEMPLATE = '''
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Identificador Inteligente de Plantas</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #2E7D32;
      --primary-dark: #1B5E20;
      --primary-light: #4CAF50;
      --secondary: #FF9800;
      --text-dark: #1E3A2C;
      --text-light: #666;
      --background: #F8FDF9;
      --card-bg: #FFFFFF;
      --shadow: 0 8px 30px rgba(0,0,0,0.08);
      --shadow-hover: 0 12px 40px rgba(0,0,0,0.12);
      --radius: 16px;
      --transition: all 0.3s ease;
    }

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
      background: var(--background);
      color: var(--text-dark);
      line-height: 1.6;
      padding: 0;
      min-height: 100vh;
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem 1rem;
    }

    .header {
      text-align: center;
      margin-bottom: 3rem;
    }

    .logo {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      margin-bottom: 1rem;
    }

    .logo-icon {
      font-size: 2.5rem;
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .logo-text {
      font-size: 2rem;
      font-weight: 700;
      background: linear-gradient(135deg, var(--text-dark), var(--primary));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .tagline {
      color: var(--text-light);
      font-size: 1.1rem;
      font-weight: 400;
    }

    .card {
      background: var(--card-bg);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 2rem;
      margin-bottom: 1.5rem;
      transition: var(--transition);
      border: 1px solid rgba(0,0,0,0.05);
    }

    .card:hover {
      box-shadow: var(--shadow-hover);
      transform: translateY(-2px);
    }

    .card-title {
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: var(--text-dark);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .card-title i {
      color: var(--primary);
    }

    .upload-area {
      border: 2px dashed #E0E0E0;
      border-radius: 12px;
      padding: 2.5rem 1rem;
      text-align: center;
      transition: var(--transition);
      background: #FAFFFA;
      cursor: pointer;
      position: relative;
    }

    .upload-area:hover {
      border-color: var(--primary-light);
      background: #F5FFF5;
    }

    .upload-area.has-file {
      border-color: var(--primary);
      background: #F0FFF0;
    }

    .upload-area.disabled {
      border-color: #cccccc;
      background: #f5f5f5;
      cursor: not-allowed;
      opacity: 0.6;
    }

    .upload-icon {
      font-size: 3rem;
      color: var(--primary-light);
      margin-bottom: 1rem;
    }

    .upload-text {
      font-size: 1.1rem;
      color: var(--text-dark);
      margin-bottom: 0.5rem;
    }

    .upload-subtext {
      color: var(--text-light);
      font-size: 0.9rem;
    }

    .file-input {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      cursor: pointer;
    }

    .file-input.disabled {
      cursor: not-allowed;
    }

    .btn {
      background: linear-gradient(135deg, var(--primary), var(--primary-light));
      color: white;
      border: none;
      padding: 1rem 2rem;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 500;
      cursor: pointer;
      transition: var(--transition);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      text-decoration: none;
    }

    .btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(46, 125, 50, 0.3);
    }

    .btn:active {
      transform: translateY(0);
    }

    .btn-block {
      width: 100%;
    }

    .btn:disabled {
      background: #cccccc;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }

    .result-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.5rem;
      margin-top: 1rem;
    }

    .result-item {
      background: #F8FFF8;
      border-radius: 12px;
      padding: 1.5rem;
      border-left: 4px solid var(--primary);
    }

    .result-label {
      font-size: 0.9rem;
      color: var(--text-light);
      text-transform: uppercase;
      font-weight: 500;
      letter-spacing: 0.5px;
      margin-bottom: 0.5rem;
    }

    .result-value {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--text-dark);
    }

    .progress-bar {
      width: 100%;
      height: 8px;
      background: #E0E0E0;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 0.5rem;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--primary), var(--primary-light));
      border-radius: 4px;
      transition: width 0.8s ease;
    }

    .file-list {
      list-style: none;
      margin-top: 1rem;
    }

    .file-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      background: #F8FFF8;
      border-radius: 8px;
      margin-bottom: 0.5rem;
      border-left: 3px solid var(--primary-light);
    }

    .file-name {
      font-weight: 500;
      color: var(--text-dark);
    }

    .file-link {
      color: var(--primary);
      text-decoration: none;
      font-size: 0.9rem;
    }

    .file-link:hover {
      text-decoration: underline;
    }

    .alert {
      padding: 1rem 1.5rem;
      border-radius: 12px;
      margin-bottom: 1rem;
      border-left: 4px solid;
    }

    .alert-success {
      background: #F0FFF4;
      border-color: var(--primary);
      color: var(--primary-dark);
    }

    .alert-error {
      background: #FFF5F5;
      border-color: #E53E3E;
      color: #C53030;
    }

    .loading {
      display: none;
      text-align: center;
      padding: 2rem;
    }

    .loading-spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #E0E0E0;
      border-top: 4px solid var(--primary);
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 1rem;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .feature-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin: 2rem 0;
    }

    .feature-item {
      text-align: center;
      padding: 1.5rem 1rem;
      background: var(--card-bg);
      border-radius: 12px;
      box-shadow: var(--shadow);
    }

    .feature-icon {
      font-size: 2rem;
      margin-bottom: 1rem;
      color: var(--primary);
    }

    .footer {
      text-align: center;
      margin-top: 3rem;
      padding-top: 2rem;
      border-top: 1px solid #E0E0E0;
      color: var(--text-light);
      font-size: 0.9rem;
    }

    /* Nuevos estilos para vista previa de imágenes */
    .image-preview-container {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
      margin-top: 1.5rem;
    }

    .image-preview {
      position: relative;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      aspect-ratio: 1;
    }

    .image-preview img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: var(--transition);
    }

    .image-preview:hover img {
      transform: scale(1.05);
    }

    .image-preview-label {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(0,0,0,0.7);
      color: white;
      padding: 0.5rem;
      font-size: 0.8rem;
      text-align: center;
    }

    .uploaded-images-section {
      margin-top: 2rem;
    }

    .results-section {
      scroll-margin-top: 2rem;
    }

    .preview-placeholder {
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f5f5f5;
      color: #999;
      font-size: 3rem;
    }

    @media (max-width: 768px) {
      .container {
        padding: 1rem;
      }
      
      .card {
        padding: 1.5rem;
      }
      
      .logo-text {
        font-size: 1.75rem;
      }
      
      .result-grid {
        grid-template-columns: 1fr;
      }

      .image-preview-container {
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header">
      <div class="logo">
        <div class="logo-icon">🌿</div>
        <div class="logo-text">Cuidado de plantas</div>
      </div>
      <p class="tagline">Identificación inteligente de plantas con IA y recomendaciones de cuidado</p>
    </div>

    <!-- Upload Card -->
    <div class="card">
      <h2 class="card-title">
        <span>📤</span> Subir Imágenes de la Planta
      </h2>
      <p style="color: var(--text-light); margin-bottom: 1.5rem;">
        Para una identificación precisa, sube dos imágenes: una de la flor y otra de la hoja.
      </p>
      
      <form method="post" enctype="multipart/form-data" action="{{ url_for('upload') }}" id="uploadForm">
        <div class="upload-area" id="uploadArea">
          <div class="upload-icon">🌿</div>
          <div class="upload-text" id="uploadText">Haz clic para seleccionar una imagen</div>
          <div class="upload-subtext">Formatos: PNG, JPG, JPEG, GIF, WEBP (Máx. 16MB)</div>
          <input type="file" name="file" accept="image/*" class="file-input" id="fileInput" {% if files and files|length >= 2 %}disabled{% endif %}>
        </div>
        
        <div id="buttonContainer">
          {% if files and files|length >= 2 %}
          <button type="button" class="btn btn-block" style="margin-top: 1.5rem;" id="analyzeBtn" onclick="analyzePlants()">
            <span>🔍</span> Analizar Planta
          </button>
          {% else %}
          <button type="submit" class="btn btn-block" style="margin-top: 1.5rem;" id="submitBtn" {% if not files or files|length == 0 %}disabled{% endif %}>
            <span>📤</span> Subir Imagen
          </button>
          {% endif %}
        </div>
      </form>

      <!-- Vista previa de imágenes subidas -->
      {% if files and not resultado %}
      <div class="uploaded-images-section">
        <h3 class="card-title" style="font-size: 1.1rem; margin-bottom: 1rem;">
          <span>🖼️</span> Imágenes listas para analizar
        </h3>
        <div class="image-preview-container" id="imagePreviews">
          {% for f in files %}
          <div class="image-preview">
            <img src="{{ url_for('uploaded_file', filename=f) }}" alt="{{ f }}">
            <div class="image-preview-label">{{ f }}</div>
          </div>
          {% endfor %}
        </div>
        <p style="color: var(--text-light); margin-top: 1rem; text-align: center;">
          {% if files|length == 1 %}
            Sube una imagen más para identificar la planta (se requieren 2 imágenes).
          {% else %}
            ¡Listo! Haz clic en "Analizar Planta" para identificar tu planta.
          {% endif %}
        </p>
      </div>
      {% endif %}

      <!-- Loading Indicator -->
      <div class="loading" id="loadingIndicator">
        <div class="loading-spinner"></div>
        <p>Analizando la planta... Esto puede tomar unos segundos.</p>
      </div>

      <!-- Flash Messages -->
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}
          <div class="alert alert-{{ 'success' if category == 'success' else 'error' }}" style="margin-top: 1.5rem;">
            {{ msg }}
          </div>
        {% endfor %}
      {% endwith %}
    </div>

    <!-- Results Section -->
    {% if resultado %}
      <div id="resultsSection" class="results-section">
        <!-- Identification Results -->
        <div class="card">
          <h2 class="card-title">
            <span>🌱</span> Resultados de Identificación
          </h2>
          <div class="result-grid">
            <div class="result-item">
              <div class="result-label">Nombre Científico</div>
              <div class="result-value">{{ resultado.nombre_cientifico }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">Nombre Común</div>
              <div class="result-value">{{ resultado.nombre_comun }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">Certeza de Identificación</div>
              <div class="result-value">{{ resultado.probabilidad }}%</div>
              <div class="progress-bar">
                <div class="progress-fill" style="width: {{ resultado.probabilidad }}%;"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Care Information -->
        {% if cuidado %}
        <div class="card">
          <h2 class="card-title">
            <span>💧</span> Guía de Cuidados
          </h2>
          <div class="result-grid">
            <div class="result-item">
              <div class="result-label">Nombre Común</div>
              <div class="result-value">{{ cuidado.nombre_comun }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">Humedad Ideal</div>
              <div class="result-value">{{ cuidado.humidity }}%</div>
              <div class="progress-bar">
                <div class="progress-fill" style="width: {{ cuidado.humidity if cuidado.humidity != 'No disponible' else 50 }}%;"></div>
              </div>
            </div>
            <div class="result-item" style="grid-column: 1 / -1;">
              <div class="result-label">Recomendación de Cuidado</div>
              <div class="result-value">{{ cuidado.care }}</div>
            </div>
          </div>
        </div>
        {% endif %}

        <!-- New Analysis Button -->
        <div class="card" style="text-align: center;">
          <a href="{{ url_for('index') }}" class="btn">
            <span>🔄</span> Realizar Nuevo Análisis
          </a>
        </div>
      </div>

    {% else %}
      <!-- Features -->
      <div class="feature-grid">
        <div class="feature-item">
          <div class="feature-icon">🔍</div>
          <h3>Identificación Precisa</h3>
          <p>Tecnología IA avanzada para identificación botánica</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">💧</div>
          <h3>Cuidados Personalizados</h3>
          <p>Recomendaciones específicas para cada planta</p>
        </div>
        
      </div>
    {% endif %}

    <!-- Footer -->
    <div class="footer">
      <p></p>
    </div>
  </div>

  <script>
    // Upload area interaction
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const buttonContainer = document.getElementById('buttonContainer');
    const uploadText = document.getElementById('uploadText');

    // Verificar si ya hay 2 imágenes para deshabilitar la subida
    function checkFileLimit() {
      const previewContainer = document.getElementById('imagePreviews');
      const existingImages = previewContainer ? previewContainer.children.length : 0;
      
      if (existingImages >= 2) {
        fileInput.disabled = true;
        uploadArea.classList.add('disabled');
        uploadText.textContent = 'Límite alcanzado (2 imágenes)';
        
        // Cambiar a botón de análisis si no existe
        if (!document.getElementById('analyzeBtn')) {
          const analyzeBtn = document.createElement('button');
          analyzeBtn.type = 'button';
          analyzeBtn.className = 'btn btn-block';
          analyzeBtn.style.marginTop = '1.5rem';
          analyzeBtn.id = 'analyzeBtn';
          analyzeBtn.innerHTML = '<span>🔍</span> Analizar Planta';
          analyzeBtn.onclick = analyzePlants;
          
          buttonContainer.innerHTML = '';
          buttonContainer.appendChild(analyzeBtn);
        }
      }
    }

    fileInput.addEventListener('change', function(e) {
      if (this.files.length > 0) {
        const fileName = this.files[0].name;
        uploadArea.classList.add('has-file');
        uploadText.textContent = `Archivo seleccionado: ${fileName}`;
        
        // Habilitar botón de envío si existe
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
          submitBtn.disabled = false;
        }
        
        // Enviar formulario automáticamente cuando se selecciona un archivo
        setTimeout(() => {
          uploadForm.submit();
        }, 100);
      }
    });

    // Función para analizar plantas
    function analyzePlants() {
      const analyzeBtn = document.getElementById('analyzeBtn');
      loadingIndicator.style.display = 'block';
      if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span>⏳</span> Analizando...';
      }
      
      // Scroll automático al indicador de carga
      setTimeout(() => {
        loadingIndicator.scrollIntoView({ 
          behavior: 'smooth',
          block: 'center'
        });
      }, 100);
      
      // Redirigir a la ruta de análisis
      setTimeout(() => {
        window.location.href = "{{ url_for('analyze') }}";
      }, 500);
    }

    // Scroll automático a resultados después del análisis
    {% if resultado %}
    window.onload = function() {
      const resultsSection = document.getElementById('resultsSection');
      if (resultsSection) {
        setTimeout(() => {
          resultsSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
          });
        }, 500);
      }
    };
    {% endif %}

    // Drag and drop functionality
    uploadArea.addEventListener('dragover', function(e) {
      e.preventDefault();
      if (!fileInput.disabled) {
        uploadArea.style.borderColor = 'var(--primary)';
        uploadArea.style.background = '#F0FFF0';
      }
    });

    uploadArea.addEventListener('dragleave', function(e) {
      e.preventDefault();
      uploadArea.style.borderColor = '';
      uploadArea.style.background = '';
    });

    uploadArea.addEventListener('drop', function(e) {
      e.preventDefault();
      uploadArea.style.borderColor = '';
      uploadArea.style.background = '';
      
      if (e.dataTransfer.files.length && !fileInput.disabled) {
        fileInput.files = e.dataTransfer.files;
        const fileName = e.dataTransfer.files[0].name;
        uploadArea.classList.add('has-file');
        uploadText.textContent = `Archivo seleccionado: ${fileName}`;
        
        // Habilitar botón de envío si existe
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
          submitBtn.disabled = false;
        }
        
        // Enviar formulario automáticamente
        setTimeout(() => {
          uploadForm.submit();
        }, 100);
      }
    });

    // Verificar límite al cargar la página
    document.addEventListener('DOMContentLoaded', function() {
      checkFileLimit();
    });
  </script>
</body>
</html>
'''

# === Utilidades ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def limpiar_uploads():
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))

# === Rutas ===
@app.route('/')
def index():
    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
    return render_template_string(HTML_TEMPLATE, files=files, resultado=None, cuidado=None)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('error', 'No se encontró el archivo en la solicitud.')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('error', 'No se seleccionó ningún archivo.')
        return redirect(url_for('index'))

    # Verificar si ya hay 2 imágenes
    existing_files = os.listdir(app.config['UPLOAD_FOLDER'])
    if len(existing_files) >= 2:
        flash('error', 'Ya has subido 2 imágenes. Haz clic en "Analizar Planta" para continuar.')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Evitar duplicados
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(save_path):
            filename = f"{base}_{counter}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1

        file.save(save_path)
        flash('success', f'Archivo guardado como: {filename}')

        files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))

        # Redirigir a index para mostrar las imágenes subidas
        return redirect(url_for('index'))
    else:
        flash('error', 'Tipo de archivo no permitido. Usa png, jpg, jpeg, gif o webp.')
        return redirect(url_for('index'))

@app.route('/analyze')
def analyze():
    """Ruta para manejar el análisis cuando se tienen 2 imágenes"""
    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
    
    if len(files) < 2:
        flash('error', 'Se necesitan 2 imágenes para el análisis.')
        return redirect(url_for('index'))
    
    # Realizar el análisis con las 2 imágenes
    img1 = os.path.join(app.config['UPLOAD_FOLDER'], files[0])
    img2 = os.path.join(app.config['UPLOAD_FOLDER'], files[1])
    
    resultado = identificar_planta(img1, img2)
    cuidado = None
    
    if resultado:
        cuidado = obtener_info_cuidado(resultado["nombre_cientifico"])

        # Publicar humedad y datos en el tópico MQTT
        if cuidado and "humidity" in cuidado:
            try:
                data_json = json.dumps({
                    "planta": cuidado["nombre_comun"],
                    "humedad": cuidado["humidity"],
                    "consejo": cuidado["care"]
                })
                mqtt_client.publish(MQTT_TOPIC, data_json)
                print(f"📤 Enviado a {MQTT_TOPIC}: {data_json}")
            except Exception as e:
                print("⚠️ Error al publicar en MQTT:", e)

    limpiar_uploads()
    flash('success', 'Las imágenes fueron eliminadas después del análisis.')

    return render_template_string(HTML_TEMPLATE, files=[], resultado=resultado, cuidado=cuidado)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    print('🚀 Iniciando servidor Flask en http://0.0.0.0:5000')
    print('📁 Carpeta de subida:', app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=5000, debug=True)