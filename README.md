# 🌿 Sistema de Riego Inteligente IoT con IA

Un sistema autónomo de cuidado de plantas que combina el Internet de las Cosas con Inteligencia Artificial. El sistema identifica la planta mediante fotografías, consulta sus necesidades específicas de humedad utilizando un modelo de lenguaje (LLM) y ajusta automáticamente los umbrales de riego en el microcontrolador ESP32.

## 📖 Descripción del Proyecto

El cuidado de las plantas suele fallar por dos razones: desconocimiento de la especie o riego inadecuado. Este proyecto soluciona ambos problemas creando un ecosistema interconectado:

1.  **Identificación Visual:** El usuario sube fotos de la planta a una interfaz web. El sistema utiliza la API de **PlantNet** para identificar la especie científica.
2.  **Consultoría Botánica con IA:** Una vez identificada, el sistema consulta a un LLM (SmolLM3 vía HuggingFace) para determinar el **porcentaje de humedad ideal** y obtener consejos de cuidado.
3.  **Telemetría y Control (MQTT):** Los parámetros ideales se envían inalámbricamente vía MQTT a un ESP32.
4.  **Riego Adaptativo:** El ESP32 actualiza su configuración en tiempo real. Si la humedad del suelo cae por debajo del umbral recomendado por la IA (y hay agua en el tanque), activa la bomba automáticamente.

## 🚀 Características Principales

  * **Interfaz Web Intuitiva:** Desarrollada en Flask, permite subir imágenes y visualizar resultados.
  * **Identificación Botánica:** Reconocimiento de especies mediante API externa.
  * **Configuración Dinámica:** El ESP32 no tiene valores fijos; aprende cuánta agua necesita la planta basándose en la respuesta de la IA.
  * **Monitoreo de Sensores:** Lectura constante de humedad de suelo y nivel del tanque de agua.
  * **Seguridad de Bomba:** Sistema de prevención que evita activar la bomba si el tanque de agua está vacío.

## 🛠️ Arquitectura y Tecnologías

### Hardware (ESP32)

  * **Microcontrolador:** ESP32 Dev Module.
  * **Sensores:** Higrómetro (Humedad de suelo) y Sensor de nivel de agua.
  * **Actuador:** Módulo Relé para bomba de agua de 5V/12V.
  * **Protocolo:** MQTT (PubSubClient) + JSON (ArduinoJson).

### Software (Servidor/Web)

  * **Backend:** Python con Flask.
  * **APIs de IA:**
      * *PlantNet:* Para reconocimiento de imágenes.
      * *HuggingFace Inference:* Para obtención de parámetros de cultivo.
  * **Comunicación:** Paho-MQTT para enlace con el ESP32.

## 📋 Requisitos de Instalación

### 1\. Configuración del Hardware (ESP32)

Este proyecto utiliza **PlatformIO**.

1.  Clona el repositorio.
2.  Abre la carpeta del firmware en VS Code con PlatformIO.
3.  Asegúrate de instalar las librerías necesarias en `platformio.ini`:
      * `PubSubClient`
      * `ArduinoJson`
4.  Configura tus credenciales WiFi y MQTT en `main.cpp` (o usa un archivo de configuración separado).
5.  Carga el código al ESP32.

### 2\. Configuración de la Web App (Python)

1.  Navega a la carpeta del servidor.
2.  Crea un entorno virtual e instala las dependencias:
    ```bash
    pip install flask requests openai paho-mqtt python-dotenv
    ```
3.  Crea un archivo `.env` en la raíz con tus claves API:
    ```env
    PLANTNET_API_KEY="tu_api_key"
    PLANTNET_PROJECT="all"
    HUGGINGFACE_API_KEY="tu_token_hf"
    HUGGINGFACE_BASE_URL="url_del_modelo"
    MQTT_BROKER="broker.hivemq.com"
    MQTT_PORT=1883
    MQTT_TOPIC="miJardin/infoPlanta"
    ```
4.  Ejecuta la aplicación:
    ```bash
    python Pagina_Riego_Inteligente.py
    ```

## 🎮 Uso del Sistema

1.  Enciende el **ESP32**. Verás en el Monitor Serie que espera datos (`"Esperando datos..."`).
2.  Abre el navegador en `http://localhost:5000`.
3.  Sube dos fotos de tu planta (hoja y flor).
4.  Presiona **"Analizar Planta"**.
5.  El sistema identificará la planta y enviará el nuevo umbral de humedad al ESP32.
6.  El ESP32 recibirá el mensaje, actualizará la variable `humedadIdealPlanta` y regará solo si es necesario según el nuevo criterio.

## 👥 Equipo de Desarrollo

Este proyecto fue realizado con éxito gracias a la colaboración de:

  * **Angel Manuel Lopez Cruz** - *Desarrollador Senior* 👨‍💻
  * **Demcy Yahir Rodríguez Gomez** - *Ingeniero de Software* 🏗️
  * **Edwin Rafael Lopez Gomez** - *Desarrollador Junior* 💻
  * **Luis Fernando De León Popoca** - *Desarrollador Junior* 🖥️

-----

*Proyecto desarrollado para la asignatura de IoT Tecnologías Computacionales II - 2025*
