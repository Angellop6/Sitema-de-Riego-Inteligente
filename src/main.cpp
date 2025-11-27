#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> 

// --- 1. CONFIGURACIÓN DE RED ---
const char* WIFI_SSID = "RI-UAEMex";
const char* WIFI_PASSWORD = "";

// --- 2. CONFIGURACIÓN MQTT ---
const char* MQTT_BROKER = "broker.hivemq.com";
const int MQTT_PORT = 1883;
const char* MQTT_CLIENT_ID = "esp32-miJardin-12345";

// Tópicos MQTT
const char* TOPIC_DATOS_SENSORES = "miJardin/datosSensores"; // Tópico para ENVIAR datos
const char* TOPIC_INFO_PLANTA = "miJardin/infoPlanta";     // Tópico para RECIBIR info

// --- 3. CONFIGURACIÓN DE PINES ---
const int SOIL_MOISTURE_PIN = 35; 
const int WATER_LEVEL_PIN   = 34; 
const int PUMP_RELAY_PIN    = 26; 

// --- 4. CALIBRACIÓN Y UMBRALES ---
const int SOIL_DRY_VALUE = 2700;
const int SOIL_WET_VALUE = 2300;
const int WATER_DRY_VALUE = 0; 
const int WATER_WET_VALUE = 1919; 

// Ya no usamos un umbral de suelo fijo.
const int WATER_THRESHOLD_PERCENT = 80; // Umbral de agua en base (para no desbordar)

const int TIEMPO_RIEGO_MS = 3000;
const long INTERVALO_LECTURA_MS = 5000; 

// --- Variables Globales ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);
unsigned long previousMillis = 0; 

// --- ¡¡NUEVAS VARIABLES GLOBALES!! ---
// Guardarán la info recibida por MQTT
String nombrePlanta = "Desconocida";
String consejoRiego = "Esperando datos...";
int humedadIdealPlanta = 30; // Umbral de riego por defecto (ej. 30%)

// --- ¡¡NUEVA FUNCIÓN!! CALLBACK DE MQTT ---
// Esta función se ejecuta CADA VEZ que llega un mensaje a un tópico suscrito
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Mensaje recibido en [");
  Serial.print(topic);
  Serial.print("]: ");
  
  // Convertir el payload (bytes) a un string
  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0';
  Serial.println(message);

  // Solo procesar si es el tópico de info de planta
  if (strcmp(topic, TOPIC_INFO_PLANTA) == 0) {
    // Parsear el JSON recibido
    StaticJsonDocument<256> doc; // 256 bytes es seguro para tu JSON
    DeserializationError error = deserializeJson(doc, message);

    if (error) {
      Serial.print("Error al parsear JSON: ");
      Serial.println(error.c_str());
      return;
    }

    // Extraer y guardar los datos en las variables globales
    nombrePlanta = doc["planta"].as<String>();
    humedadIdealPlanta = doc["humedad"]; // ¡Este es el nuevo umbral de riego!
    consejoRiego = doc["consejo"].as<String>();

    Serial.println("--- ¡Nuevos datos de planta recibidos! ---");
    Serial.print("Planta: "); Serial.println(nombrePlanta);
    Serial.print("Humedad Ideal (Umbral): "); Serial.println(humedadIdealPlanta);
    Serial.print("Consejo: "); Serial.println(consejoRiego);
    Serial.println("----------------------------------------");
  }
}

// --- FUNCIÓN DE CONTROL DE BOMBA (Sin cambios) ---
void controlarBomba(bool encender) {
  if (encender) {
    Serial.println(">> ¡Activando bomba (Relé en LOW)!");
    digitalWrite(PUMP_RELAY_PIN, LOW);
  } else {
    Serial.println(">> Bomba detenida (Relé en HIGH).");
    digitalWrite(PUMP_RELAY_PIN, HIGH);
  }
}

// --- FUNCIÓN DE CONECTAR A WIFI (Sin cambios) ---
void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n¡Conectado a WiFi!");
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

// --- ¡¡FUNCIÓN RECONNECT MQTT MODIFICADA!! ---
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Intentando conexión MQTT...");
    if (mqttClient.connect(MQTT_CLIENT_ID)) {
      Serial.println("¡Conectado a MQTT!");
      
      // ¡¡SUSCRIBIRSE AL TÓPICO DE INFO!!
      // Después de conectar, le decimos al broker qué tópicos queremos escuchar
      mqttClient.subscribe(TOPIC_INFO_PLANTA);
      Serial.print("Suscrito a: ");
      Serial.println(TOPIC_INFO_PLANTA);
      
    } else {
      Serial.print("falló, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" -> Intentando de nuevo en 5 segundos");
      delay(5000);
    }
  }
}

// --- FUNCIÓN DE PUBLICACIÓN DE DATOS (Sin cambios) ---
// Sigue enviando los datos de los sensores
void publicarDatosSensores(int humedad, int nivelAgua) {
  StaticJsonDocument<128> doc;
  doc["Nivel de humedad"] = humedad;
  doc["Nivel de agua"] = nivelAgua;

  char output[128];
  serializeJson(doc, output);

  Serial.print("Publicando datos de sensores: ");
  Serial.println(output);
  
  mqttClient.publish(TOPIC_DATOS_SENSORES, output);
}

// --- ¡¡SETUP MODIFICADO!! ---
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n--- Sistema de Riego IoT v4.0 (Subscriber) ---");

  pinMode(PUMP_RELAY_PIN, OUTPUT);
  controlarBomba(false);

  setupWiFi(); 
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  
  // ¡¡AÑADIR ESTA LÍNEA!!
  // Le dice a la librería MQTT qué función debe ejecutar cuando llegue un mensaje
  mqttClient.setCallback(mqttCallback); 
}

// --- ¡¡LOOP MODIFICADO!! ---
void loop() {
  // 1. Manejar conexiones
  if (WiFi.status() != WL_CONNECTED) {
    setupWiFi(); 
  }
  if (!mqttClient.connected()) {
    reconnectMQTT(); // Si nos conectamos, aquí es donde se suscribe
  }
  mqttClient.loop(); // ¡¡CRÍTICO!! Esta línea revisa si han llegado mensajes

  // 2. Temporizador
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= INTERVALO_LECTURA_MS) {
    previousMillis = currentMillis; 

    // --- 3. Lógica de Sensores (Sin cambios) ---
    int soilMoistureRaw = analogRead(SOIL_MOISTURE_PIN);
    int waterLevelRaw = analogRead(WATER_LEVEL_PIN);

    int soilMoisturePercent = map(soilMoistureRaw, SOIL_DRY_VALUE, SOIL_WET_VALUE, 0, 100);
    soilMoisturePercent = constrain(soilMoisturePercent, 0, 100);

    int waterLevelPercent = map(waterLevelRaw, WATER_DRY_VALUE, WATER_WET_VALUE, 0, 100);
    waterLevelPercent = constrain(waterLevelPercent, 0, 100);

    Serial.println("---------------------------------------------");
    Serial.print("Humedad Actual: ");
    Serial.print(soilMoisturePercent);
    Serial.print("% | Humedad Ideal: ");
    Serial.print(humedadIdealPlanta); // Imprime el umbral dinámico
    Serial.print("% | Nivel Agua: ");
    Serial.print(waterLevelPercent);
    Serial.println("%");
    
    // --- 4. ¡¡LÓGICA DE RIEGO MODIFICADA!! ---
    // Compara la humedad leída (soilMoisturePercent) con la ideal (humedadIdealPlanta)
    if (soilMoisturePercent < humedadIdealPlanta && waterLevelPercent < WATER_THRESHOLD_PERCENT) {
      Serial.print("CONDICIÓN: Humedad (");
      Serial.print(soilMoisturePercent);
      Serial.print("%) es MENOR que la ideal (");
      Serial.print(humedadIdealPlanta);
      Serial.println("%). ¡Iniciando riego!");
      
      controlarBomba(true);
      delay(TIEMPO_RIEGO_MS); 
      controlarBomba(false);
      Serial.println("Riego completado.");
      
    } else {
      Serial.print("CONDICIÓN: No se requiere riego. ");
      if (soilMoisturePercent >= humedadIdealPlanta) {
        Serial.print("(Suelo suficientemente húmedo).");
      }
      if (waterLevelPercent >= WATER_THRESHOLD_PERCENT) {
        Serial.print("(Nivel de agua en base es alto).");
      }
      Serial.println();
    }

    // --- 5. Publicar Datos (Sin cambios) ---
    publicarDatosSensores(soilMoisturePercent, waterLevelPercent);
  }
}
