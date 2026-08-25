#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <ESP32Servo.h>

//CONFIGURAÇÃO — AJUSTE ANTES DE FAZER O UPLOAD
const char* WIFI_SSID  = "NOME_DA_SUA_REDE";
const char* WIFI_SENHA = "SENHA_DA_SUA_REDE";

// IP da máquina rodando "python app.py", na mesma rede WiFi do ESP32.
// Descubra com "ipconfig" (Windows) -> IPv4 da rede WiFi.
const char* API_HOST = "http://:5000";


const float DISTANCIA_VAZIO = 20.0;  // cm, sensor até o fundo (vazio)
const float DISTANCIA_CHEIO = 3.0;   // cm, sensor até a água (cheio)
#define PINO_DHT           4
#define PINO_TRIG          5
#define PINO_ECHO          18
#define PINO_POTENCIOMETRO 34
#define PINO_PIEZO         35
#define PINO_BOTAO         32
#define PINO_RELE          33
#define PINO_SERVO         25
#define PINO_LED_VERDE     26
#define PINO_LED_AMARELO   27
#define PINO_LED_VERMELHO  13
#define PINO_BUZZER        19
#define DHTTIPO DHT22
DHT dht(PINO_DHT, DHTTIPO);
Servo servoRisco;


//ESTADO DO SISTEMA
bool operacaoAtiva = false;
unsigned long inicioOperacao = 0;
float horasUsoAcumuladas = 0;   // 1 minuto real = 1 "hora" simulada
float limiteAlertaServidor = 70;
String modoOperacaoServidor = "alerta";
unsigned long ultimaSincronizacao = 0;
const unsigned long INTERVALO_SINCRONIZACAO = 15000; // 15s
unsigned long ultimoEnvio = 0;
const unsigned long INTERVALO_ENVIO = 10000; // 10s
unsigned long ultimoDebounce = 0;
int estadoBotaoAnterior = HIGH;


//Setup
void setup() {

  Serial.begin(115200);

  pinMode(PINO_TRIG, OUTPUT);
  pinMode(PINO_ECHO, INPUT);
  pinMode(PINO_BOTAO, INPUT_PULLUP);
  pinMode(PINO_RELE, OUTPUT);
  pinMode(PINO_LED_VERDE, OUTPUT);
  pinMode(PINO_LED_AMARELO, OUTPUT);
  pinMode(PINO_LED_VERMELHO, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);

  // A maioria dos módulos de relé baratos é "ativo em LOW".
  // HIGH aqui = relé desligado (bomba sem energia).
  digitalWrite(PINO_RELE, HIGH);

  dht.begin();

  servoRisco.attach(PINO_SERVO);
  servoRisco.write(0);

  conectarWiFi();

  Serial.println("Vortex Field Unit iniciado.");
}

//// LOOP PRINCIPAL
void loop() {

  atualizarBotao();

  if (operacaoAtiva) {
    unsigned long agora = millis();
    horasUsoAcumuladas = (agora - inicioOperacao) / 60000.0;
  }

  float temperatura = dht.readTemperature();
  float umidade = dht.readHumidity();

  if (isnan(temperatura)) temperatura = 25; // fallback se o sensor falhar
  if (isnan(umidade)) umidade = 50;

  float nivelReservatorio = lerNivelReservatorio();
  int vibracao = analogRead(PINO_PIEZO);
  int cargaEquipamento = map(analogRead(PINO_POTENCIOMETRO), 0, 4095, 0, 100);

  float risco = calcularRiscoLocal(
    horasUsoAcumuladas,
    temperatura,
    nivelReservatorio,
    vibracao
  );

  if (millis() - ultimaSincronizacao > INTERVALO_SINCRONIZACAO) {
    sincronizarConfiguracao();
    ultimaSincronizacao = millis();
  }

  bool bloqueado = (
    risco >= limiteAlertaServidor &&
    modoOperacaoServidor == "bloqueio"
  );
  atualizarAtuadores(risco, bloqueado);
  if (millis() - ultimoEnvio > INTERVALO_ENVIO) {

    enviarLeituraParaServidor(
      horasUsoAcumuladas,
      nivelReservatorio,
      temperatura,
      umidade,
      vibracao,
      cargaEquipamento
    );
    ultimoEnvio = millis();
  }
  imprimirStatus(
    risco,
    temperatura,
    umidade,
    nivelReservatorio,
    vibracao,
    cargaEquipamento,
    bloqueado
  );

  delay(300);
}

// WiFi
void conectarWiFi() {

  Serial.print("Conectando ao WiFi");
  WiFi.begin(WIFI_SSID, WIFI_SENHA);

  int tentativas = 0;

  while (WiFi.status() != WL_CONNECTED && tentativas < 20) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado! IP do ESP32: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nNao foi possivel conectar ao WiFi. Rodando em modo local (sem servidor).");
  }
}

//Sensor de nível do reservatório (combustível e água)
float lerNivelReservatorio() {

  digitalWrite(PINO_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);

  long duracao = pulseIn(PINO_ECHO, HIGH, 30000); // timeout de 30ms

  if (duracao == 0) return -1; // sensor não respondeu

  float distanciaCm = duracao * 0.0343 / 2.0;

  float nivel = (DISTANCIA_VAZIO - distanciaCm) /
                (DISTANCIA_VAZIO - DISTANCIA_CHEIO) * 100.0;

  nivel = constrain(nivel, 0, 100);

  return nivel;
}

//Botão de ligar/desligar a operação
void atualizarBotao() {

  int leitura = digitalRead(PINO_BOTAO);
  if (leitura != estadoBotaoAnterior) {
    ultimoDebounce = millis();
  }

  if ((millis() - ultimoDebounce) > 50) {

    if (leitura == LOW && estadoBotaoAnterior == HIGH) {

      operacaoAtiva = !operacaoAtiva;

      if (operacaoAtiva) {
        inicioOperacao = millis() - (unsigned long)(horasUsoAcumuladas * 60000);
        Serial.println(">> Operacao iniciada");
      } else {
        Serial.println(">> Operacao parada");
      }
    }
  }

  estadoBotaoAnterior = leitura;
}

// Risco local — failsafe, funciona mesmo sem o servidor
float calcularRiscoLocal(float horas, float temperatura, float nivelReservatorio, int vibracao) {

  float riscoHoras = min(horas * 10.0, 100.0);

  float riscoTemp = 0;
  if (temperatura > 35) {
    riscoTemp = (temperatura - 35) * (100.0 / 25.0); // 35C=0 ... 60C=100
  }

  float riscoNivel = 0;
  if (nivelReservatorio >= 0 && nivelReservatorio < 20) {
    riscoNivel = (20 - nivelReservatorio) * 5;
  }

  float riscoVibracao = (vibracao > 1000) ? 40 : 0;

  float riscoTotal =
    (riscoHoras    * 0.40) +
    (riscoTemp     * 0.25) +
    (riscoNivel    * 0.25) +
    (riscoVibracao * 0.10);

  return constrain(riscoTotal, 0, 100);
}

// Atuadores: LEDs, buzzer, servo e relé
void atualizarAtuadores(float risco, bool bloqueado) {

  digitalWrite(PINO_LED_VERDE,    risco < 50);
  digitalWrite(PINO_LED_AMARELO,  risco >= 50 && risco < 70);
  digitalWrite(PINO_LED_VERMELHO, risco >= 70);

  int angulo = map((int)risco, 0, 100, 0, 180);
  servoRisco.write(angulo);

  if (risco >= 70) {
    tone(PINO_BUZZER, 1000, 200);
  }

  // Ajuste para LOW/HIGH conforme o seu módulo de relé específico.
  digitalWrite(PINO_RELE, bloqueado ? LOW : HIGH);
}

// Comunicação com a API (Flask)
void sincronizarConfiguracao() {

  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(String(API_HOST) + "/api/configuracao");

  int codigo = http.GET();

  if (codigo == 200) {

    String resposta = http.getString();

    JsonDocument doc;
    deserializeJson(doc, resposta);

    limiteAlertaServidor = doc["limite_alerta"] | 70;
    modoOperacaoServidor = doc["modo_operacao"].as<String>();

    Serial.println(
      "Config sincronizada: limite=" + String(limiteAlertaServidor) +
      " modo=" + modoOperacaoServidor
    );

  } else {
    Serial.println("Falha ao sincronizar configuracao (codigo " + String(codigo) + ")");
  }

  http.end();
}

void enviarLeituraParaServidor(
  float horas,
  float nivel,
  float temperatura,
  float umidade,
  int vibracao,
  int carga
) {

  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(String(API_HOST) + "/api/monitorar");
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["horas_uso"] = horas;
  doc["combustivel"] = nivel;
  doc["temperatura"] = temperatura;
  doc["umidade"] = umidade;
  doc["vibracao"] = vibracao;
  doc["carga_equipamento"] = carga;

  String corpo;
  serializeJson(doc, corpo);

  int codigo = http.POST(corpo);

  if (codigo == 200) {
    Serial.println("Leitura enviada ao servidor com sucesso.");
  } else {
    Serial.println("Falha ao enviar leitura (codigo " + String(codigo) + ")");
  }

  http.end();
}

// Debug no Serial Monitor
void imprimirStatus(
  float risco,
  float temperatura,
  float umidade,
  float nivel,
  int vibracao,
  int carga,
  bool bloqueado
) {
  Serial.println("Operacao ativa: " + String(operacaoAtiva ? "sim" : "nao"));
  Serial.println("Horas de uso:   " + String(horasUsoAcumuladas, 2));
  Serial.println("Temperatura:    " + String(temperatura) + " C");
  Serial.println("Umidade:        " + String(umidade) + " %");
  Serial.println("Reservatorio:   " + String(nivel) + " %");
  Serial.println("Vibracao (raw): " + String(vibracao));
  Serial.println("Carga (pot):    " + String(carga) + " %");
  Serial.println("Risco:          " + String(risco, 1) + "%");
  Serial.println("Modo servidor:  " + modoOperacaoServidor + " (limite " + String(limiteAlertaServidor) + ")");
  Serial.println("Bloqueado:      " + String(bloqueado ? "SIM" : "nao"));
}