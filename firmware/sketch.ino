
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>
#include <math.h>

// ==================== WIFI ====================
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// ==================== THINGSBOARD ====================
const char* TB_SERVER = "thingsboard.cloud";
const int TB_PORT = 1883;
const char* TB_TOKEN = "WoFT2ZjpnJxfpnDa58BG";
const char* TB_TOPIC = "v1/devices/me/telemetry";

// ==================== HIVEMQ - BAI 2 ====================
const char* PY_SERVER = "broker.hivemq.com";
const int PY_PORT = 1883;
const char* PY_TOPIC = "ptit/b23dccn311/iot_bai2/telemetry";

// ==================== CAM BIEN ====================
const int DHT_PIN = 15;
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int LED_PIN = 2;

// ==================== CHU KY GUI ====================
const unsigned long SEND_INTERVAL_MS = 5000;

// ==================== MQTT CLIENT ====================
WiFiClient tbWifiClient;
WiFiClient pyWifiClient;

PubSubClient tbMqtt(tbWifiClient);
PubSubClient pyMqtt(pyWifiClient);

DHTesp dht;

unsigned long lastSend = 0;
unsigned long sequenceNo = 0;

// ==================== KET NOI WIFI ====================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);

  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// ==================== KET NOI THINGSBOARD ====================
void connectThingsBoard() {
  while (!tbMqtt.connected()) {
    String clientId =
        "ESP32-TB-" +
        String((uint32_t)ESP.getEfuseMac(), HEX);

    Serial.print("Connecting ThingsBoard...");

    if (tbMqtt.connect(
          clientId.c_str(),
          TB_TOKEN,
          NULL)) {
      Serial.println(" connected");
    } else {
      Serial.printf(
        " failed, rc=%d. Retry in 2 seconds\n",
        tbMqtt.state()
      );

      delay(2000);
    }
  }
}

// ==================== KET NOI HIVEMQ ====================
void connectHiveMQ() {
  while (!pyMqtt.connected()) {
    String clientId =
        "ESP32-PY-" +
        String((uint32_t)ESP.getEfuseMac(), HEX);

    Serial.print("Connecting HiveMQ...");

    if (pyMqtt.connect(clientId.c_str())) {
      Serial.println(" connected");
    } else {
      Serial.printf(
        " failed, rc=%d. Retry in 2 seconds\n",
        pyMqtt.state()
      );

      delay(2000);
    }
  }
}

// ==================== DO KHOANG CACH ====================
float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration =
      pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return NAN;
  }

  return duration * 0.0343f / 2.0f;
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  dht.setup(DHT_PIN, DHTesp::DHT22);

  connectWiFi();

  tbMqtt.setServer(TB_SERVER, TB_PORT);
  pyMqtt.setServer(PY_SERVER, PY_PORT);

  tbMqtt.setBufferSize(512);
  pyMqtt.setBufferSize(512);

  Serial.println("ESP32 IoT Bai 1 + Bai 2");
}

// ==================== LOOP ====================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!tbMqtt.connected()) {
    connectThingsBoard();
  }

  if (!pyMqtt.connected()) {
    connectHiveMQ();
  }

  tbMqtt.loop();
  pyMqtt.loop();

  unsigned long now = millis();

  if (now - lastSend < SEND_INTERVAL_MS) {
    return;
  }

  lastSend = now;

  // Doc cam bien DHT22
  TempAndHumidity data =
      dht.getTempAndHumidity();

  // Doc cam bien HC-SR04
  float distance = readDistanceCm();

  // Kiem tra du lieu
  if (!isfinite(data.temperature) ||
      !isfinite(data.humidity) ||
      !isfinite(distance)) {
    Serial.println(
      "Invalid sensor data - skip publish"
    );
    return;
  }

  sequenceNo++;

  // Tao JSON telemetry
  char payload[256];

  snprintf(
    payload,
    sizeof(payload),
    "{\"temperature\":%.2f,"
    "\"humidity\":%.2f,"
    "\"distance_cm\":%.2f,"
    "\"rssi\":%d,"
    "\"sequence\":%lu,"
    "\"uptime_s\":%lu}",
    data.temperature,
    data.humidity,
    distance,
    WiFi.RSSI(),
    sequenceNo,
    millis() / 1000
  );

  // Gui du lieu den ThingsBoard
  bool tbOK =
      tbMqtt.publish(TB_TOPIC, payload);

  // Gui cung du lieu den HiveMQ cho Python
  bool pyOK =
      pyMqtt.publish(PY_TOPIC, payload);

  // In ket qua len Serial Monitor
  Serial.println("--------------------------------");
  Serial.print("JSON: ");
  Serial.println(payload);

  Serial.printf(
    "ThingsBoard: %s\n",
    tbOK ? "OK" : "FAILED"
  );

  Serial.printf(
    "HiveMQ: %s\n",
    pyOK ? "OK" : "FAILED"
  );

  // Nhan LED bao hieu
  digitalWrite(LED_PIN, HIGH);
  delay(80);
  digitalWrite(LED_PIN, LOW);
}
