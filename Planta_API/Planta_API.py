import requests
import json

# 🔑 Clave de API de PlantNet
API_KEY = "2b10Jve3fUU1g2LNP2Joj2G9iO"

# 🌍 Puedes especificar una flora más concreta si quieres (ej: "america")
PROJECT = "all"

# 📡 Endpoint de la API
api_endpoint = f"https://my-api.plantnet.org/v2/identify/{PROJECT}?api-key={API_KEY}"

# 📸 Rutas de las imágenes de la planta
image_path_1 = "C:/Users/luisf/OneDrive/Documentos/PlatformIO/Projects/ProyectoRiegoInteligente/Planta_API/imgs/orq.jpg"
image_path_2 = "C:/Users/luisf/OneDrive/Documentos/PlatformIO/Projects/ProyectoRiegoInteligente/Planta_API/imgs/orq1.jpg"

# 📤 Abrir y enviar las imágenes a la API
with open(image_path_1, 'rb') as img1, open(image_path_2, 'rb') as img2:
    files = [
        ('images', (image_path_1, img1)),
        ('images', (image_path_2, img2))
    ]
    data = {'organs': ['flower', 'leaf']}
    
    # 🚀 Enviar la solicitud POST
    response = requests.post(api_endpoint, files=files, data=data)
    result = response.json()

# 🧾 Verificar si la respuesta fue exitosa
if response.status_code == 200:
    print("\n✅ Conexión exitosa con la API de PlantNet.\n")

    # 🌱 Mostrar solo el resultado más relevante
    if "results" in result and len(result["results"]) > 0:
        plant = result["results"][0]  # Primer resultado = más probable

        nombre_cientifico = plant["species"]["scientificNameWithoutAuthor"]
        nombre_comun = plant["species"].get("commonNames", ["No disponible"])
        probabilidad = round(plant["score"] * 100, 2)

        print("🌿 Resultado más probable:\n")
        print(f"🌱 Nombre científico: {nombre_cientifico}")
        print(f"🏷️ Nombre común: {', '.join(nombre_comun)}")
        print(f"📊 Certeza de identificación: {probabilidad}%\n")
    else:
        print("❌ No se pudo identificar ninguna planta en las imágenes.")
else:
    print(f"❌ Error al conectar con la API. Código de estado: {response.status_code}")
