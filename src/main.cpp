#include <Arduino.h>

// --- Configuración del Sensor de Nivel de Agua ---
const int WATER_SENSOR_PIN = 34; // Usamos GPIO34 (ADC1_CH6)

// --- Configuración del Sensor de Humedad del Suelo (HW-390) ---
const int SOIL_MOISTURE_PIN = 35; // Usamos GPIO35 (ADC1_CH7)

void setup() {
  // Inicia la comunicación serial a 115200 baudios
  Serial.begin(115200);
  Serial.println("\nIniciando lectura de sensores...");
}

void loop() {
  // --- 1. Lectura del Sensor de Nivel de Agua ---
  // El ADC del ESP32 tiene una resolución de 12 bits (0-4095)
  int waterSensorValue = analogRead(WATER_SENSOR_PIN);

  // Mapea el valor a un porcentaje. ¡NECESITAS CALIBRAR ESTO!
  int water_valor_seco = 0;    // Calibrar con sensor fuera del agua
  int water_valor_mojado = 2500; // Calibrar con sensor sumergido
  int waterLevelPercent = map(waterSensorValue, water_valor_seco, water_valor_mojado, 0, 100);
  waterLevelPercent = constrain(waterLevelPercent, 0, 100);


  // --- 2. Lectura del Sensor de Humedad del Suelo ---
  int soilMoistureValue = analogRead(SOIL_MOISTURE_PIN);

  // Mapea el valor a un porcentaje. NOTA: para este sensor, un valor más bajo significa más humedad.
  // Por eso invertimos el mapeo (de 4095 a 0).
  int soil_valor_seco = 4095;    // Calibrar con sensor al aire
  int soil_valor_mojado = 1500;  // Calibrar con sensor en tierra muy húmeda
  int soilMoisturePercent = map(soilMoistureValue, soil_valor_seco, soil_valor_mojado, 0, 100);
  soilMoisturePercent = constrain(soilMoisturePercent, 0, 100);

  // --- Imprime todos los datos en el Monitor Serie ---
  Serial.println("--------------------");
  Serial.print("Nivel de agua (raw): ");
  Serial.print(waterSensorValue);
  Serial.print(" -> Porcentaje: ");
  Serial.print(waterLevelPercent);
  Serial.println("%");

  Serial.print("Humedad del suelo (raw): ");
  Serial.print(soilMoistureValue);
  Serial.print(" -> Porcentaje: ");
  Serial.print(soilMoisturePercent);
  Serial.println("%");
  
  // Espera 2 segundos entre lecturas
  delay(2000);
}