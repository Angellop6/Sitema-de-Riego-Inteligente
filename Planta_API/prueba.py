from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, flash
from werkzeug.utils import secure_filename
import os
import requests
import json
import re
from openai import OpenAI
import paho.mqtt.client as mqtt  # 🆕 NUEVO: para publicar datos al ESP32 vía 
from dotenv import load_dotenv
load_dotenv()

# === Configuración general ===
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



# 🆕 Crear y conectar cliente MQTT
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


# === HTML ===
HTML_TEMPLATE = '''
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Identificador de Plantas 🌿</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial; padding: 1rem; background: #f6f8fa; }
    .container { max-width: 520px; margin: 0 auto; }
    .card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 1rem; margin-bottom: 1rem; }
    input[type=file] { width: 100%; padding: .5rem 0; }
    button { width: 100%; padding: .75rem; border: none; border-radius: 8px; font-size: 1rem; background: #2e7d32; color: white; }
    button:hover { background: #256628; cursor: pointer; }
    .success { color: green; }
    .error { color: red; }
    ul { padding-left: 1rem; }
  </style>
</head>
<body>
  <div class="container">
    <h2>🌿 Identificador de Plantas</h2>
    <div class="card">
      <form method="post" enctype="multipart/form-data" action="{{ url_for('upload') }}">
        <input type="file" name="file" accept="image/*" required>
        <br><br>
        <button type="submit">Subir imagen</button>
      </form>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}
          <p class="{{ category }}">{{ msg }}</p>
        {% endfor %}
      {% endwith %}
    </div>

    {% if resultado %}
      <div class="card">
        <h3>🌱 Resultado más probable</h3>
        <p><b>Nombre científico:</b> {{ resultado.nombre_cientifico }}</p>
        <p><b>Nombre común:</b> {{ resultado.nombre_comun }}</p>
        <p><b>Certeza:</b> {{ resultado.probabilidad }}%</p>
      </div>

      {% if cuidado %}
      <div class="card">
        <h3>💧 Cuidado de la planta</h3>
        <p><b>Humedad ideal:</b> {{ cuidado.humidity }}%</p>
        <p><b>Nombre común:</b> {{ cuidado.nombre_comun }}</p>
        <p><b>Consejo:</b> {{ cuidado.care }}</p>
      </div>
      {% endif %}
    {% else %}
      <div class="card">
        <h3>Imágenes subidas</h3>
        {% if files|length == 0 %}
          <p>No hay imágenes todavía.</p>
        {% else %}
          <ul>
            {% for f in files %}
              <li><a href="{{ url_for('uploaded_file', filename=f) }}" target="_blank">{{ f }}</a></li>
            {% endfor %}
          </ul>
          <p>Sube una imagen más para identificar la planta.</p>
        {% endif %}
      </div>
    {% endif %}
  </div>
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
        flash(('error', 'No se encontró el archivo en la solicitud.'))
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash(('error', 'No se seleccionó ningún archivo.'))
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
        flash(('success', f'Archivo guardado como: {filename}'))

        files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))

        if len(files) >= 2:
            img1 = os.path.join(app.config['UPLOAD_FOLDER'], files[-2])
            img2 = os.path.join(app.config['UPLOAD_FOLDER'], files[-1])
            resultado = identificar_planta(img1, img2)

            cuidado = None
            if resultado:
                cuidado = obtener_info_cuidado(resultado["nombre_cientifico"])

                # 🆕 === Publicar humedad y datos en el tópico MQTT ===
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
            flash(('success', 'Las imágenes fueron eliminadas después del análisis.'))

            return render_template_string(HTML_TEMPLATE, files=[], resultado=resultado, cuidado=cuidado)
        else:
            return redirect(url_for('index'))
    else:
        flash(('error', 'Tipo de archivo no permitido. Usa png, jpg, jpeg, gif o webp.'))
        return redirect(url_for('index'))


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    print('🚀 Iniciando servidor Flask en http://0.0.0.0:5000')
    print('📁 Carpeta de subida:', app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=5000, debug=True)
