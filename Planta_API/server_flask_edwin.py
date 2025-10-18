from flask import Flask, render_template, request, send_from_directory
import os

app = Flask(__name__)

# 📂 Carpeta donde se guardarán las fotos
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    images = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', images=images)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template('index.html', message='⚠️ No se envió ningún archivo')

    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', message='⚠️ No se seleccionó ningún archivo')

    if file and allowed_file(file.filename):
        # 🗑️ Eliminar todas las imágenes anteriores
        for old_file in os.listdir(app.config['UPLOAD_FOLDER']):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], old_file))

        # 💾 Guardar la nueva imagen
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        return render_template(
            'index.html',
            message=f'✅ Imagen subida correctamente: {file.filename}',
            images=[file.filename]
        )
    else:
        return render_template(
            'index.html',
            message='❌ Tipo de archivo no permitido (usa JPG, PNG, JPEG o GIF)',
            images=os.listdir(app.config['UPLOAD_FOLDER'])
        )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)