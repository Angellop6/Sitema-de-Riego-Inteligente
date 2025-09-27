#include <Arduino.h>
#include <WiFi.h>
#include "credentials.h" // Incluimos nuestro archivo de credenciales

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.print("Conectando a la red WiFi: ");
  Serial.println(ssid);

  // Iniciar conexión WiFi
  WiFi.begin(ssid, password);

  // Esperar a que la conexión se establezca
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("¡WiFi conectado!");
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // El loop puede quedar vacío para este ejemplo
  delay(1000);
}